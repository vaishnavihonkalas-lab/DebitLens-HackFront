"""Short paraphrases of provider documentation retrieved 23 October 2026."""

GUIDES = [
    {
        "channel": "GOOGLE_PLAY",
        "title": "Google Play subscription",
        "url": "https://support.google.com/googleplay/answer/7018481",
        "checked": "2026-10-23",
        "steps": [
            "Use the Google account that purchased the subscription.",
            "Open Google Play subscriptions, select the plan, and follow its cancellation flow.",
            "Keep the confirmation and the end-of-access date.",
        ],
        "note": "Removing the app does not end a subscription. Payment-plan obligations can remain.",
    },
    {
        "channel": "APPLE",
        "title": "Apple subscription",
        "url": "https://support.apple.com/en-in/118428",
        "checked": "2026-10-23",
        "steps": [
            "On iPhone, open Settings and your Apple Account.",
            "Open Subscriptions, choose the plan and follow the cancellation option.",
            "Check the displayed expiry and retain confirmation.",
        ],
        "note": "If Apple did not bill it, identify the actual billing company first.",
    },
    {
        "channel": "UPI",
        "title": "UPI mandate through Google Pay",
        "url": "https://support.google.com/pay/india/answer/10840624?hl=en-GB",
        "checked": "2026-10-23",
        "steps": [
            "In Google Pay, open your profile and Autopay.",
            "Inspect the correct live mandate and available pause/cancel controls.",
            "Authenticate only inside your payment app and verify its resulting status.",
        ],
        "note": "App and mandate restrictions vary, including loans. Revoking payment permission does not terminate a service contract.",
    },
    {
        "channel": "NETFLIX_DIRECT",
        "title": "Netflix direct membership",
        "url": "https://help.netflix.com/en/node/407",
        "checked": "2026-10-23",
        "steps": [
            "Open Netflix membership management in your own account.",
            "Follow cancellation through its final confirmation.",
            "Keep the confirmation email and effective end date.",
        ],
        "note": "For partner billing, follow the billing provider. Demo services are fictional and are not Netflix.",
    },
    {
        "channel": "DIRECT",
        "title": "Direct merchant billing",
        "url": None,
        "checked": None,
        "steps": [
            "Identify the merchant from a receipt.",
            "Use its official account or customer support to request cancellation.",
            "Retain the request and effective-date confirmation.",
        ],
        "note": "Generic guidance, not a provider-verified cancellation route.",
    },
    {
        "channel": "CARD",
        "title": "Card or bank mandate",
        "url": None,
        "checked": None,
        "steps": [
            "Use the issuing bank’s official mandate-management channel.",
            "Check whether you are cancelling the service or just payment permission.",
            "Retain confirmation and monitor later statements.",
        ],
        "note": "Bank-specific steps are not verified. Existing contractual obligations may remain.",
    },
    {
        "channel": "UNKNOWN",
        "title": "Billing channel not established",
        "url": None,
        "checked": None,
        "steps": [
            "Check the original receipt to identify who bills you.",
            "Confirm the billing channel before selecting instructions.",
        ],
        "note": "Do not guess a cancellation route from a processor description.",
    },
]
