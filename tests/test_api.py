import os
import uuid
from datetime import datetime, timezone

TEST_DB_NAME = "attendance_test_" + uuid.uuid4().hex[:8]
os.environ["MONGO_DB"] = TEST_DB_NAME

from fastapi.testclient import TestClient
from app.main import app, db


def make_employee():
    emp_code = "EMP" + str(uuid.uuid4().int % 1_000_000).zfill(6)
    employee = {
        "emp_code": emp_code,
        "name": "Test Employee",
        "email": f"{emp_code.lower()}@example.com",
        "department": "Engineering",
        "shift_start": "09:30",
        "shift_end": "18:30",
        "joined_on": datetime.now(timezone.utc).date().isoformat(),
    }
    return emp_code, employee


def make_punch_times():
    punch_in_ms = int(datetime.now(timezone.utc).timestamp() * 1000) - 7200000
    punch_out_ms = punch_in_ms + 3600000
    return punch_in_ms, punch_out_ms


def create_test_employee(client):
    emp_code, employee = make_employee()
    response = client.post("/employees", json=employee)
    assert response.status_code == 201, response.text
    return emp_code


def punch_in_employee(client, emp_code, punch_in_ms):
    response = client.post(
        "/attendance/punch-in",
        json={
            "emp_code": emp_code,
            "status": "PRESENT",
            "punched_at": punch_in_ms,
        },
    )
    assert response.status_code == 201, response.text
    return response


def punch_out_employee(client, emp_code, punch_out_ms):
    return client.post(
        "/attendance/punch-out",
        json={"emp_code": emp_code, "punched_at": punch_out_ms},
    )


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_employee_list_pagination():
    with TestClient(app) as client:
        response = client.get(
            "/employees", params={"page": 1, "page_size": 20}
        )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["page_size"] == 20


def test_page_size_over_limit_is_rejected():
    with TestClient(app) as client:
        response = client.get(
            "/employees", params={"page": 1, "page_size": 101}
        )
    assert response.status_code == 422


def test_uses_separate_test_database():
    assert db.name == TEST_DB_NAME
    assert db.name != "attendance_db"


def test_punch_in_and_punch_out():
    emp_code, employee = make_employee()
    punch_in_ms, punch_out_ms = make_punch_times()

    with TestClient(app) as client:
        create_response = client.post("/employees", json=employee)
        assert create_response.status_code == 201, create_response.text

        punch_response = punch_in_employee(client, emp_code, punch_in_ms)
        assert punch_response.json()["emp_code"] == emp_code

        out_response = punch_out_employee(client, emp_code, punch_out_ms)
        assert out_response.status_code == 200, out_response.text

        result = out_response.json()
        assert result["punch_out"] == punch_out_ms
        assert result["work_hours"] >= 0


def test_duplicate_punch_out_is_rejected():
    punch_in_ms, punch_out_ms = make_punch_times()

    with TestClient(app) as client:
        emp_code = create_test_employee(client)
        punch_in_employee(client, emp_code, punch_in_ms)

        first_out = punch_out_employee(client, emp_code, punch_out_ms)
        assert first_out.status_code == 200, first_out.text

        second_out = punch_out_employee(
            client, emp_code, punch_out_ms + 60000
        )
        assert second_out.status_code == 409, second_out.text
        assert "Already punched out" in second_out.text


def test_attendance_correction_records_history():
    punch_in_ms, punch_out_ms = make_punch_times()

    with TestClient(app) as client:
        emp_code = create_test_employee(client)
        punch_in_employee(client, emp_code, punch_in_ms)

        out_response = punch_out_employee(client, emp_code, punch_out_ms)
        assert out_response.status_code == 200, out_response.text

        record = out_response.json()
        attendance_date = record["date"]
        corrected_punch_out = punch_out_ms + 300000

        correction_response = client.patch(
            f"/attendance/{emp_code}/{attendance_date}",
            json={
                "punch_out": corrected_punch_out,
                "reason": "Testing correction history",
                "regularized_by": "test_admin",
            },
        )
        assert correction_response.status_code == 200, correction_response.text

        corrected = correction_response.json()
        expected_original = punch_out_ms
        expected_corrected = corrected_punch_out

        assert corrected["punch_out"] == expected_corrected
        assert len(corrected["history"]) >= 1

        latest_history = corrected["history"][-1]
        assert latest_history["by"] == "test_admin"
        assert latest_history["reason"] == "Testing correction history"
        assert latest_history["changes"]["punch_out"]["from"] == expected_original
        assert latest_history["changes"]["punch_out"]["to"] == expected_corrected
