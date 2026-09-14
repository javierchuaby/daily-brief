"""Patches for coursemology-py library to fix validation issues.

This module patches the _handle_response method to handle missing filter field
in submissions API responses.

Issue: The coursemology-py library expects a 'filter' field in the
submissions API response, but the actual API doesn't include it.

Fix: Patch BaseAPI._handle_response to make a raw HTTP request when
validation fails to bypass the model validation.

This patch is applied at module import time and affects only submissions
validation. All other functionality remains unchanged.
"""

from __future__ import annotations


def patch_coursemology():
    """Patch coursemology-py to handle missing filter field in submissions API."""
    try:
        import coursemology_py.models.course.submissions as subs_module
        from coursemology_py.api.base import BaseAPI
    except ImportError:
        return  # Library not installed, nothing to patch

    # Store original _handle_response
    original_handle_response = BaseAPI._handle_response

    def patched_handle_response(self, response, response_model=None):
        result = original_handle_response(self, response, response_model)

        if response_model is subs_module.TopLevelSubmissionsIndexResponse and result:
            if (
                not hasattr(result.meta_data, "filter")
                or result.meta_data.filter is None
            ):
                base_url = self._base_url
                prefix = self._url_prefix
                url = f"{base_url.rstrip('/')}/{prefix.lstrip('/')}"
                raw_resp = self._session.get(url, params={"format": "json"})
                if raw_resp.status_code == 200:
                    result.meta_data.filter = subs_module.SubmissionsFilterData(
                        assessments=[], groups=[], users=[]
                    )
        return result

    BaseAPI._handle_response = patched_handle_response
