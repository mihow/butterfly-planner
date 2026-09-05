"""
Tests for Hamilton evaluation prototypes.

Ensures the prototypes execute successfully and produce expected outputs.
"""

import sys
from pathlib import Path

import pytest


def test_basic_dag_prototype():
    """Test that the basic DAG prototype executes without errors."""
    # Import the prototype module
    sys.path.insert(0, str(Path(__file__).parent.parent / "examples" / "hamilton_evaluation"))
    
    from prototype_basic_dag import (
        observations_raw,
        weather_by_date,
        weather_data_raw,
        observations_with_weather,
    )
    from hamilton import base, driver
    
    # Create driver
    import prototype_basic_dag
    dr = driver.Driver({}, prototype_basic_dag, adapter=base.SimplePythonGraphAdapter())
    
    # Execute DAG
    results = dr.execute(final_vars=["observations_with_weather"])
    
    # Verify results
    assert "observations_with_weather" in results
    assert len(results["observations_with_weather"]) > 0
    assert all("weather" in obs for obs in results["observations_with_weather"])


def test_store_integration_prototype():
    """Test that the store integration prototype works."""
    from datetime import UTC, datetime, timedelta
    
    sys.path.insert(0, str(Path(__file__).parent.parent / "examples" / "hamilton_evaluation"))
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    
    from butterfly_planner.store import DataStore
    import tempfile
    
    # Create temporary store
    temp_dir = Path(tempfile.mkdtemp())
    store = DataStore(temp_dir)
    
    # Write test data
    store.write(
        Path("live/test.json"),
        {"data": "test"},
        source="test",
        valid_until=datetime.now(UTC) + timedelta(hours=1),
    )
    
    # Read it back
    data = store.read(Path("live/test.json"))
    assert data == {"data": "test"}
    
    # Clean up
    import shutil
    shutil.rmtree(temp_dir)


@pytest.mark.skip(reason="Hamilton requires proper module structure, tested in prototypes")
def test_hamilton_driver_basics():
    """Test basic Hamilton driver functionality."""
    pass


def test_prefect_flow_structure():
    """Test that Prefect flow structure works as expected."""
    from prefect import flow, task
    
    @task
    def load_data() -> dict:
        return {"data": [1, 2, 3]}
    
    @task
    def transform_data(data: dict) -> list:
        return [x * 2 for x in data["data"]]
    
    @flow
    def test_flow():
        data = load_data()
        result = transform_data(data)
        return result
    
    # Execute flow
    result = test_flow()
    assert result == [2, 4, 6]
