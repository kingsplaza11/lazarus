"""Property tests for status choice validation. Validates: Requirements 6.3"""
import pytest
from django.core.exceptions import ValidationError
from hypothesis import given, strategies as st

from intake.models import Corpse

VALID_STATUSES = {"pending", "running", "done", "failed"}


@given(value=st.text().filter(lambda s: s not in VALID_STATUSES))
def test_prop_status_rejects_unknown_values(value):
    """**Validates: Requirements 6.3**"""
    corpse = Corpse(name="x", status=value)
    with pytest.raises(ValidationError) as exc:
        corpse.full_clean(validate_unique=False)
    assert "status" in exc.value.message_dict


@pytest.mark.parametrize("value", sorted(VALID_STATUSES))
def test_valid_statuses_pass_validation(value):
    """**Validates: Requirements 6.3**"""
    Corpse(name="x", status=value).full_clean(validate_unique=False)
