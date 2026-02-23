"""Live API test - call the actual handler methods end-to-end."""
import asyncio
import json
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

from realize.tools.dynamic_report_handlers import get_dynamic_report_settings, get_dynamic_report_data


async def main():
    account_id = "pumikademoaccount"

    # Test 1: Settings
    print("=" * 70)
    print("TEST 1: get_dynamic_report_settings")
    print("=" * 70)
    result = await get_dynamic_report_settings({"account_id": account_id})
    text = result[0].text
    has_error = "Error" in text or "❌" in text
    print(f"Status: {'FAIL' if has_error else 'OK'}")
    print(f"Length: {len(text)} chars")
    print(text[:800])
    print("...\n")

    # Test 2: Basic data query
    print("=" * 70)
    print("TEST 2: get_dynamic_report_data — campaign name + clicks + spent (7d)")
    print("=" * 70)
    result = await get_dynamic_report_data({
        "account_id": account_id,
        "columns": [
            "PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_NAME",
            "PERFORMANCE_REPORT.METRICS.CLICKS",
            "PERFORMANCE_REPORT.METRICS.SPENT",
        ],
        "date_preset": "LAST_7_DAYS",
    })
    text = result[0].text
    has_error = "Error" in text or "❌" in text
    print(f"Status: {'FAIL' if has_error else 'OK'}")
    print(f"Length: {len(text)} chars")
    print(text)
    print()

    # Test 3: More columns + filter
    print("=" * 70)
    print("TEST 3: get_dynamic_report_data — with status filter + more metrics (30d)")
    print("=" * 70)
    result = await get_dynamic_report_data({
        "account_id": account_id,
        "columns": [
            "PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_NAME",
            "PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_STATUS",
            "PERFORMANCE_REPORT.METRICS.VISIBLE_IMPRESSIONS",
            "PERFORMANCE_REPORT.METRICS.CLICKS",
            "PERFORMANCE_REPORT.METRICS.SPENT",
            "PERFORMANCE_REPORT.METRICS.CTR",
        ],
        "date_preset": "LAST_30_DAYS",
        "filters": [
            {"name": "PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_STATUS", "operator": "IN", "values": ["RUNNING"]}
        ],
    })
    text = result[0].text
    has_error = "Error" in text or "❌" in text
    print(f"Status: {'FAIL' if has_error else 'OK'}")
    print(f"Length: {len(text)} chars")
    print(text)
    print()

    # Test 4: Day-level breakdown
    print("=" * 70)
    print("TEST 4: get_dynamic_report_data — day-level breakdown (7d)")
    print("=" * 70)
    result = await get_dynamic_report_data({
        "account_id": account_id,
        "columns": [
            "PERFORMANCE_REPORT.TIME_UNITS.DAY",
            "PERFORMANCE_REPORT.METRICS.VISIBLE_IMPRESSIONS",
            "PERFORMANCE_REPORT.METRICS.CLICKS",
            "PERFORMANCE_REPORT.METRICS.SPENT",
        ],
        "date_preset": "LAST_7_DAYS",
    })
    text = result[0].text
    has_error = "Error" in text or "❌" in text
    print(f"Status: {'FAIL' if has_error else 'OK'}")
    print(f"Length: {len(text)} chars")
    print(text)
    print()

    # Test 5: Country breakdown
    print("=" * 70)
    print("TEST 5: get_dynamic_report_data — country breakdown (30d)")
    print("=" * 70)
    result = await get_dynamic_report_data({
        "account_id": account_id,
        "columns": [
            "PERFORMANCE_REPORT.TARGETING.COUNTRY.NAME",
            "PERFORMANCE_REPORT.METRICS.VISIBLE_IMPRESSIONS",
            "PERFORMANCE_REPORT.METRICS.CLICKS",
            "PERFORMANCE_REPORT.METRICS.SPENT",
        ],
        "date_preset": "LAST_30_DAYS",
    })
    text = result[0].text
    has_error = "Error" in text or "❌" in text
    print(f"Status: {'FAIL' if has_error else 'OK'}")
    print(f"Length: {len(text)} chars")
    print(text)
    print()

    # Test 6: Validation errors
    print("=" * 70)
    print("TEST 6: Validation — missing columns")
    print("=" * 70)
    result = await get_dynamic_report_data({
        "account_id": account_id,
        "date_preset": "LAST_7_DAYS",
    })
    print(f"Status: OK (expected error)")
    print(result[0].text)
    print()

    print("=" * 70)
    print("TEST 7: Validation — missing date_preset")
    print("=" * 70)
    result = await get_dynamic_report_data({
        "account_id": account_id,
        "columns": ["PERFORMANCE_REPORT.METRICS.CLICKS"],
    })
    print(f"Status: OK (expected error)")
    print(result[0].text)
    print()

    print("=" * 70)
    print("TEST 8: Validation — numeric account_id")
    print("=" * 70)
    result = await get_dynamic_report_data({
        "account_id": "12345",
        "columns": ["PERFORMANCE_REPORT.METRICS.CLICKS"],
        "date_preset": "LAST_7_DAYS",
    })
    print(f"Status: OK (expected error)")
    print(result[0].text)


if __name__ == "__main__":
    asyncio.run(main())
