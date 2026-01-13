# TDD Tests for Incomplete Features

This document tracks test files written using TDD methodology where the implementation has not been completed. These tests are currently skipped in CI to allow passing builds.

**Last Updated:** 2026-01-13

## Summary

| Test File | Feature | Status | Priority |
|-----------|---------|--------|----------|
| test_buddy_models.py | Buddy System Models | Not Started | Medium |
| test_buddy_services.py | Buddy System Services | Not Started | Medium |
| test_dive_buddy.py | Dive Buddy Relationships | Not Started | Medium |
| test_diver_selectors.py | Diver Profile Selectors | Not Started | Low |
| test_email_settings.py | Email Settings Singleton | Not Started | Low |
| test_email_templates.py | DB Email Templates | Not Started | Low |
| test_mobile_models.py | Mobile App Models | Partial | High |
| test_party_relationship_forms.py | Party Relationship Forms | Not Started | Medium |
| test_recurring_models.py | Recurring Excursion Models | Not Started | High |
| test_recurring_services.py | Recurring Excursion Services | Partial | High |
| test_webrtc_consumer.py | WebRTC Signaling | Not Started | Low |
| test_courseware_recommendations.py | Courseware Recommendations | Not Started | Medium |
| test_cms_access.py | CMS Entitlement Access | Not Started | Low |
| test_entitlements.py | Entitlement Services | Not Started | Medium |
| test_fulfillment.py | Order Fulfillment | Not Started | Medium |
| TestCreateLedgerEntriesIntegration | Ledger Entry Integration | Needs Update | Low |

---

## Detailed Breakdown

### 1. Buddy System (`test_buddy_models.py`, `test_buddy_services.py`)

**Purpose:** Allow divers to manage buddy relationships and dive teams.

**Models Needed:**
- `Contact` - Track external contacts (not yet registered users)
- `BuddyIdentity` - Unified identity for Person or Contact
- `DiveTeam` - Group of divers who dive together
- `DiveTeamMember` - Membership in a dive team

**Services Needed:**
- `get_or_create_identity()` - Create/get buddy identity
- `add_buddy_pair()` - Create 2-person buddy team
- `create_buddy_group()` - Create 3+ person dive group
- `list_buddy_pairs()` - List person's buddy pairs
- `list_buddy_groups()` - List person's dive groups
- `remove_buddy()` - Leave/delete buddy relationship

**Test Count:** 48 tests (27 models + 21 services)

---

### 2. Dive Buddy Legacy (`test_dive_buddy.py`)

**Purpose:** Original dive buddy model for tracking buddy relationships.

**Note:** May be superseded by Buddy System above.

**Models Needed:**
- `DiveBuddy` - Simple buddy relationship model

**Test Count:** 8 tests

---

### 3. Diver Selectors (`test_diver_selectors.py`)

**Purpose:** Optimized queries for staff diver detail view.

**Functions Needed:**
- `calculate_age()` - Calculate age from date of birth
- `get_diver_detail()` - Full diver profile with all related data
- `get_diver_certifications()` - Diver's certifications
- `get_diver_equipment()` - Diver's owned equipment
- `get_diver_booking_history()` - Past bookings
- `get_diver_dive_log_stats()` - Aggregate dive statistics

**Test Count:** 22 tests

---

### 4. Email Settings (`test_email_settings.py`)

**Purpose:** Database-first SES email configuration (like AISettings pattern).

**Models Needed:**
- `EmailSettings` - Singleton for email config (from_email, SES region, etc.)

**Services Needed:**
- `get_email_backend()` - Get configured email backend
- `send_templated_email()` - Send email using DB template

**Test Count:** 19 tests

---

### 5. Email Templates (`test_email_templates.py`)

**Purpose:** Store email templates in database for easy editing.

**Models Needed:**
- `EmailTemplate` - Template with subject, body, required context fields

**Services Needed:**
- `render_email_template()` - Render template with context
- `validate_template_context()` - Validate required fields present

**Test Count:** 22 tests

---

### 6. Mobile Models (`test_mobile_models.py`)

**Purpose:** Models for mobile app functionality.

**Models Status:**
- `AppVersion` - **Exists, needs migration updates**
- `LocationUpdate` - **Exists in django-geo primitive**
- `LocationSharingPreference` - **Exists in django-geo primitive**
- `FCMDevice` - Push notification device registration
- `PushNotificationLog` - Log of sent push notifications

**Note:** Core models exist but tests reference fields that may have changed.

**Test Count:** 21 tests

---

### 7. Party Relationship Forms (`test_party_relationship_forms.py`)

**Purpose:** Forms using django-parties PartyRelationship instead of legacy models.

**Forms Needed:**
- `EmergencyContactForm` - Create emergency contact as PartyRelationship
- `DiverRelationshipForm` - Create general relationship as PartyRelationship

**Models Needed:**
- `DiverRelationshipMeta` - Extended metadata for diver relationships

**Test Count:** 14 tests

---

### 8. Recurring Excursions (`test_recurring_models.py`, `test_recurring_services.py`)

**Purpose:** Manage recurring dive excursions (weekly trips, etc.).

**Models Needed:**
- `RecurrenceRule` - RRULE-based recurrence pattern
- `ExcursionSeries` - Template for recurring excursions
- `SeriesException` - Exceptions to recurrence (cancelled, rescheduled, added)

**Services Status:**
- `sync_series_occurrences()` - **Exists but tests fail**
- `cancel_occurrence()` - Needs implementation
- `edit_occurrence()` - Needs implementation
- `edit_series()` - Needs implementation
- `split_series()` - Needs implementation

**Note:** Partial implementation exists. Services exist but don't match test expectations.

**Test Count:** 43 tests (18 models + 25 services)

---

### 9. WebRTC Signaling (`test_webrtc_consumer.py`)

**Purpose:** WebSocket consumer for WebRTC video calling.

**Consumer Needed:**
- `WebRTCConsumer` - Handle WebRTC signaling messages

**Features:**
- User connection tracking
- Call initiation (call, incoming_call, user_offline)
- SDP exchange (offer, answer)
- ICE candidate exchange
- Call end (hangup, reject)

**Note:** Requires pytest-asyncio configuration to run tests.

**Test Count:** 11 tests

---

## How to Enable Tests

When implementing a feature:

1. Remove the `pytestmark = pytest.mark.skip()` line from the test file
2. Implement the feature following TDD
3. Run tests: `POSTGRES_HOST=localhost python -m pytest src/diveops/operations/tests/test_<feature>.py -v`
4. Iterate until all tests pass
5. Commit with "Implements T-XXX: <feature>"

---

## Priority Order Recommendation

1. **High Priority** (Core Business Features):
   - Recurring Excursions (test_recurring_models.py, test_recurring_services.py)
   - Mobile Models (test_mobile_models.py)

2. **Medium Priority** (User Experience):
   - Buddy System (test_buddy_models.py, test_buddy_services.py, test_dive_buddy.py)
   - Party Relationship Forms (test_party_relationship_forms.py)

3. **Low Priority** (Admin/Operations):
   - Email Settings (test_email_settings.py)
   - Email Templates (test_email_templates.py)
   - Diver Selectors (test_diver_selectors.py)
   - WebRTC (test_webrtc_consumer.py) - Nice to have for video calls
