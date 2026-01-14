"""Management command to publish the Buceo Feliz app article."""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from django_cms_core.models import (
    BlogCategory,
    ContentPage,
    AccessLevel,
    PageStatus,
    PageType,
)
from django_cms_core.services import add_block, publish_page


User = get_user_model()


ARTICLE = {
    "slug": "your-local-friend-buceo-feliz-app",
    "title": "Your Local Friend in Paradise: How the Buceo Feliz App Keeps You Connected",
    "category_slug": "safety",
    "excerpt": "When you're exploring a new destination, having a trusted local contact can make all the difference. The Buceo Feliz app puts a local friend in your pocket.",
    "featured_image_url": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=1200",
    "reading_time_minutes": 5,
    "tags": ["app", "safety", "travel", "mexico", "customer service", "technology"],
    "blocks": [
        {
            "type": "rich_text",
            "data": {
                "content": """<p>When visiting a new destination, especially one where you might not speak the language fluently, having a trusted local contact can transform your entire experience. For many travelers coming to dive in Mexico, their dive professional becomes much more than an instructor or guide—they become a trusted advisor and, often, a friend.</p>

<p>At Happy Diving, we've built our reputation on this relationship. We're often the sole point of contact for visitors exploring Cozumel and the Riviera Maya. Our guests ask us about the best restaurants, how to get around safely, where to find the best tacos, and what to do when plans change unexpectedly. We're not just here to take you diving—we're here to help make your entire vacation memorable and worry-free.</p>"""
            },
        },
        {
            "type": "heading",
            "data": {"text": "A Local Friend, Just a Message Away", "level": 2},
        },
        {
            "type": "rich_text",
            "data": {
                "content": """<p>That's why we created the <strong>Buceo Feliz</strong> app. It puts a local friend right in your pocket, available whenever you need us.</p>

<p>The app's <strong>real-time chat</strong> feature means you can reach our team instantly. Lost and need directions? Message us. Restaurant recommendation? We've got you. Medical emergency and need help communicating with local services? We're there. No waiting on hold, no language barriers—just quick, personal assistance from people who know you and know the area.</p>"""
            },
        },
        {
            "type": "heading",
            "data": {"text": "Peace of Mind Through Location Sharing", "level": 2},
        },
        {
            "type": "rich_text",
            "data": {
                "content": """<p>One of the app's most valued features is <strong>optional location sharing</strong>. When you're exploring unfamiliar areas—whether hiking to a cenote, taking a taxi to a remote beach, or navigating downtown at night—you can share your location with our team.</p>

<p>This isn't about surveillance. It's about peace of mind. Your family back home knows you have a local contact watching out for you. And you know that if something goes wrong, someone nearby can coordinate help immediately.</p>

<p>Many solo travelers and families have told us this feature alone made them feel significantly more comfortable exploring beyond the resort zone.</p>"""
            },
        },
        {
            "type": "heading",
            "data": {"text": "Beyond Diving: Your Vacation Concierge", "level": 2},
        },
        {
            "type": "rich_text",
            "data": {
                "content": """<p>As dive professionals, we're naturally focused on safety. We track weather conditions, currents, and marine life patterns. But our role as trusted advisors extends far beyond the water.</p>

<p>Through the app, you can:</p>
<ul>
<li><strong>View your upcoming dives</strong> with all the details</li>
<li><strong>Update your gear sizing</strong> so we have everything ready</li>
<li><strong>Share your certifications</strong> for seamless verification</li>
<li><strong>Access emergency contacts</strong> for local services</li>
<li><strong>Chat directly</strong> with our team in real-time</li>
</ul>

<p>It's everything you need to feel confident and connected during your visit.</p>"""
            },
        },
        {
            "type": "heading",
            "data": {"text": "What's Coming Next", "level": 2},
        },
        {
            "type": "rich_text",
            "data": {
                "content": """<p>We're constantly improving the Buceo Feliz app based on guest feedback. Here's what we're working on:</p>

<ul>
<li><strong>Emergency Quick-Dial</strong> — One-tap access to local emergency services, hospitals, and the U.S. Consulate, with automatic translation assistance</li>
<li><strong>Local Recommendations</strong> — Curated tips for restaurants, activities, and hidden gems, pushed directly to guests based on their interests</li>
<li><strong>Transportation Integration</strong> — Trusted taxi and transfer services bookable directly through the app</li>
<li><strong>Activity Check-Ins</strong> — Safety confirmations for non-diving activities, so someone always knows where you are</li>
<li><strong>Medical Information Sharing</strong> — Secure storage of allergies, medications, and emergency contacts accessible to first responders</li>
</ul>

<p>Our goal is simple: whether you're 30 meters underwater or exploring ancient ruins, you should feel like you have a local friend looking out for you.</p>"""
            },
        },
        {
            "type": "heading",
            "data": {"text": "Download the App", "level": 2},
        },
        {
            "type": "rich_text",
            "data": {
                "content": """<p>The Buceo Feliz app is available for Android devices. Download it before your trip and connect with us—we'll be ready to help from the moment you land.</p>

<p>Because in an unfamiliar place, the most valuable thing you can have isn't a guidebook or a translation app. It's a friend who knows the area, speaks the language, and genuinely cares about your experience.</p>

<p>That's what Happy Diving offers. That's what Buceo Feliz means.</p>

<p><em>Happy Diving. Buceo Feliz.</em></p>"""
            },
        },
        {
            "type": "call_to_action",
            "data": {
                "title": "Get the Buceo Feliz App",
                "text": "Download the app and connect with your local dive team before your trip.",
                "button_text": "Download for Android",
                "button_url": "/app/",
            },
        },
    ],
}


class Command(BaseCommand):
    help = "Publish the Buceo Feliz app article to the blog"

    def handle(self, *args, **options):
        # Get or create admin user for authorship
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(self.style.ERROR("No superuser found. Create one first."))
            return

        # Get category
        try:
            category = BlogCategory.objects.get(slug=ARTICLE["category_slug"])
        except BlogCategory.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Category '{ARTICLE['category_slug']}' not found. Run seed_blog first.")
            )
            return

        # Check if article already exists
        if ContentPage.objects.filter(slug=ARTICLE["slug"]).exists():
            self.stdout.write(
                self.style.WARNING(f"Article '{ARTICLE['slug']}' already exists. Skipping.")
            )
            return

        # Create the blog post
        post = ContentPage.objects.create(
            slug=ARTICLE["slug"],
            title=ARTICLE["title"],
            page_type=PageType.POST,
            status=PageStatus.DRAFT,
            access_level=AccessLevel.PUBLIC,
            category=category,
            excerpt=ARTICLE["excerpt"],
            featured_image_url=ARTICLE["featured_image_url"],
            reading_time_minutes=ARTICLE["reading_time_minutes"],
            tags=ARTICLE["tags"],
            seo_title=ARTICLE["title"],
            seo_description=ARTICLE["excerpt"],
            og_image_url=ARTICLE["featured_image_url"],
        )

        self.stdout.write(f"Created draft post: {post.title}")

        # Add content blocks
        for block_data in ARTICLE["blocks"]:
            add_block(
                page=post,
                block_type=block_data["type"],
                data=block_data["data"],
            )

        self.stdout.write(f"Added {len(ARTICLE['blocks'])} content blocks")

        # Publish the post
        publish_page(post, admin_user)

        self.stdout.write(
            self.style.SUCCESS(
                f"Published article: {post.title}\n"
                f"URL: /blog/{post.slug}/"
            )
        )
