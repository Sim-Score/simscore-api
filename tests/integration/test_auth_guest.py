import pytest
from app.core.config import settings

@pytest.mark.order(2)  # Run guest tests second
@pytest.mark.guest
def test_guest_user_flow(locally_running_client):
    """Test guest user functionality"""
    # Guest user specific tests... 