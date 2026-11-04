import pytest
from redis.exceptions import ConnectionError

from app.cache import JsonCache
from app.database import Base, make_database
from app.models_db import ReportRow
from app.repositories.report_repository_sql import ReportRepositorySql
from app.services.report_service import ReportService, DuplicateReportError
from app.schemas.report import ReportCreate

class MemoryRedis:
    """Test double only; does not replace the real Redis exercise."""
    def __init__(self):
        self.values = {}
        self.expirations = {}
        self.down = False

    def check(self):
        if self.down:
            raise ConnectionError("Simulated outage")

    def get(self, key):
        self.check()
        return self.values.get(key)

    def set(self, key, value, ex):
        self.check()
        self.values[key] = value
        self.expirations[key] = ex

    def delete(self, key):
        self.check()
        self.values.pop(key, None)
        self.expirations.pop(key, None)

    def ping(self):
        self.check()
        return True

    def close(self):
        # No sockets to release; compatible with FastAPI lifespan cleanup.
        pass


def test_fake_supports_readiness_and_cleanup():
    client = MemoryRedis()
    assert client.ping() is True
    client.down = True
    with pytest.raises(ConnectionError):
        client.ping()
    client.close()  # Closing resources must also work during an outage.


@pytest.fixture
def setup(tmp_path):
    url = "sqlite:///" + (tmp_path / "test.db").as_posix()
    engine, sessions = make_database(url)
    Base.metadata.create_all(engine)
    repo = ReportRepositorySql(sessions)
    service = ReportService(repo)
    
    with sessions.begin() as db:
        row = ReportRow(
            department_id=1,
            reported_by="Jan Kowalski",
            report_type="Hardware",
            description="Uszkodzona klawiatura",
            status="unsolved"
        )
        db.add(row)
        db.flush()
        report_id = row.id

    client = MemoryRedis()
    cache = JsonCache(client, ttl=30, resource_name="report")
    yield url, repo, service, client, cache, report_id
    engine.dispose()


def test_persists_with_new_engine(setup):
    url, _, _, _, _, report_id = setup
    engine, sessions = make_database(url)
    try:
        new_repo = ReportRepositorySql(sessions)
        new_service = ReportService(new_repo)
        assert new_service.get_report(report_id).reported_by == "Jan Kowalski"
    finally:
        engine.dispose()


def test_duplicate_rolls_back(setup):
    _, _, service, _, _, _ = setup
    
    with pytest.raises((ValueError, DuplicateReportError)):
        service.create_report(ReportCreate(
            department_id=1,
            reported_by="Anna Nowak",
            report_type="Software",
            description="Uszkodzona klawiatura"  
        ))
    assert len(service.get_all_reports()) == 1


def test_miss_hit_and_invalidation(setup, monkeypatch):
    _, repo, _, client, cache, report_id = setup
    reads = []
    original_get = repo.get

    def counted_get(rid):
        reads.append(rid)
        return original_get(rid)

    monkeypatch.setattr(repo, "get", counted_get)
    
    key = cache.key(report_id)
    
    cached, source = cache.get(report_id)
    assert source == "MISS"

    report_data = repo.get(report_id).model_dump(mode="json")
    cache.put(report_id, report_data)
    assert client.expirations[key] == 30

    reads.clear()
    cached_val, source_hit = cache.get(report_id)
    assert source_hit == "HIT"
    assert len(reads) == 0  

    repo.delete(report_id)
    cache.delete(report_id)
    assert key not in client.expirations


def test_failed_cache_set_still_returns_database_value(setup, monkeypatch):
    _, _, service, client, cache, report_id = setup

    def failed_set(*args, **kwargs):
        raise ConnectionError("SET failed")

    monkeypatch.setattr(client, "set", failed_set)
    
    report = service.get_report(report_id)
    payload = report.model_dump(mode="json")
    success = cache.put(report_id, payload)
    
    assert success is False
    assert report.reported_by == "Jan Kowalski"


def test_outage_does_not_block_read_or_commit(setup):
    _, repo, _, client, cache, report_id = setup
    client.down = True
    
    cached, source = cache.get(report_id)
    assert source == "BYPASS"
    
    assert repo.delete(report_id) is True


def test_corrupt_cache_and_missing_record(setup):
    _, _, service, client, cache, report_id = setup
    key = cache.key(report_id)
    client.values[key] = "not-json"
    
    val, source = cache.get(report_id)
    assert source == "MISS"
    
    with pytest.raises(Exception):
        service.get_report(99999)  
