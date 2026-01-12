"""Management command to seed CMS content."""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from django_cms_core.models import CMSSettings, ContentPage, AccessLevel, PageStatus
from django_cms_core.services import create_page, add_block, publish_page


User = get_user_model()


class Command(BaseCommand):
    help = "Seed CMS settings and initial pages"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Delete existing pages and recreate",
        )

    def handle(self, *args, **options):
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(self.style.ERROR("No superuser found. Create one first."))
            return

        settings = CMSSettings.get_instance()
        settings.site_name = "Happy Diving"
        settings.default_seo_title_suffix = " | Happy Diving - Playa del Carmen"
        settings.save()
        self.stdout.write(self.style.SUCCESS("CMSSettings configured"))

        pages_config = [
            {
                "slug": "home",
                "title": "Happy Diving - Scuba Diving in Playa del Carmen",
                "access_level": AccessLevel.PUBLIC,
                "blocks": [
                    # Hero Section
                    {
                        "type": "hero",
                        "data": {
                            "title": "Dive Into Paradise",
                            "subtitle": "Experience the magic of the Caribbean Sea with Playa del Carmen's friendliest dive team",
                            "background_url": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=1920",
                            "cta_text": "Book Your Dive",
                            "cta_url": "/contact/",
                        },
                    },
                    # Services Section
                    {
                        "type": "heading",
                        "data": {"text": "Our Diving Adventures", "level": 2},
                    },
                    {
                        "type": "rich_text",
                        "data": {
                            "content": """<div class="services-grid">
<div class="service-card">
<h3>PADI Certification Courses</h3>
<p>From your first breath underwater to professional certifications. Open Water, Advanced, Rescue Diver, and Divemaster courses available.</p>
</div>
<div class="service-card">
<h3>Fun Dives</h3>
<p>Already certified? Join us for 2-tank morning dives exploring the stunning Mesoamerican Reef - the world's second-largest barrier reef.</p>
</div>
<div class="service-card">
<h3>Cenote Diving</h3>
<p>Discover the mystical underwater caves unique to the Yucatan Peninsula. Crystal-clear freshwater, ancient stalactites, and unforgettable experiences.</p>
</div>
<div class="service-card">
<h3>Night Dives</h3>
<p>Experience the reef come alive after dark. See octopus, lobster, sleeping fish, and bioluminescent creatures on our evening adventures.</p>
</div>
</div>""",
                        },
                    },
                    # Divider
                    {"type": "divider", "data": {}},
                    # Gallery Section
                    {
                        "type": "heading",
                        "data": {"text": "Underwater Moments", "level": 2},
                    },
                    {
                        "type": "image_gallery",
                        "data": {
                            "images": [
                                {
                                    "url": "https://images.unsplash.com/photo-1682687220742-aba13b6e50ba?w=800",
                                    "alt": "Sea turtle swimming over coral reef",
                                },
                                {
                                    "url": "https://images.unsplash.com/photo-1559825481-12a05cc00344?w=800",
                                    "alt": "Colorful tropical fish on the reef",
                                },
                                {
                                    "url": "https://images.unsplash.com/photo-1635329512578-6fb15f2cb87b?w=800",
                                    "alt": "Diver exploring cenote cave",
                                },
                                {
                                    "url": "https://images.unsplash.com/photo-1544551763-77ef2d0cfc6c?w=800",
                                    "alt": "Divers descending into blue water",
                                },
                                {
                                    "url": "https://images.unsplash.com/photo-1583212292454-1fe6229603b7?w=800",
                                    "alt": "Spotted eagle ray gliding past",
                                },
                                {
                                    "url": "https://images.unsplash.com/photo-1596414086775-a1f87c7f33c2?w=800",
                                    "alt": "Pristine coral reef formation",
                                },
                            ],
                            "columns": 3,
                        },
                    },
                    # Divider
                    {"type": "divider", "data": {}},
                    # Testimonials Section
                    {
                        "type": "heading",
                        "data": {"text": "What Divers Say", "level": 2},
                    },
                    {
                        "type": "rich_text",
                        "data": {
                            "content": """<div class="testimonials">
<blockquote>
<p>"Best diving experience of my life! The cenotes were absolutely magical and the guides were incredibly knowledgeable and patient."</p>
<cite>— Sarah M., California</cite>
</blockquote>
<blockquote>
<p>"Got my Open Water certification here and couldn't be happier. Small groups, personal attention, and amazing dive sites. Highly recommend!"</p>
<cite>— James T., London</cite>
</blockquote>
<blockquote>
<p>"We've been diving all over the Caribbean and Happy Diving is hands down the best operation we've experienced. Professional, fun, and safe."</p>
<cite>— Marco & Elena, Italy</cite>
</blockquote>
</div>""",
                        },
                    },
                    # Divider
                    {"type": "divider", "data": {}},
                    # About Section
                    {
                        "type": "heading",
                        "data": {"text": "About Happy Diving", "level": 2},
                    },
                    {
                        "type": "rich_text",
                        "data": {
                            "content": """<p>Happy Diving was founded with one mission: to share the incredible underwater world of the Riviera Maya with divers from around the globe. Based in the heart of Playa del Carmen, we're just steps from the beach and minutes from the world-famous Cozumel reefs.</p>
<p>Our team of PADI-certified instructors and divemasters brings decades of combined experience and a genuine passion for marine conservation. We keep our groups small to ensure personalized attention and unforgettable experiences.</p>
<p>Whether you're taking your first breaths underwater or you're a seasoned diver seeking new adventures, we're here to make every dive your best dive yet.</p>""",
                        },
                    },
                    # Divider
                    {"type": "divider", "data": {}},
                    # Contact Section
                    {
                        "type": "heading",
                        "data": {"text": "Visit Us", "level": 2},
                    },
                    {
                        "type": "rich_text",
                        "data": {
                            "content": """<div class="contact-info">
<p><strong>Location:</strong> Playa del Carmen, Quintana Roo, Mexico</p>
<p><strong>Phone:</strong> <a href="tel:+529841234567">+52 984 123 4567</a></p>
<p><strong>WhatsApp:</strong> <a href="https://wa.me/529841234567">+52 984 123 4567</a></p>
<p><strong>Email:</strong> <a href="mailto:info@happydiving.mx">info@happydiving.mx</a></p>
<p><strong>Hours:</strong> Daily 7:00 AM - 6:00 PM</p>
</div>""",
                        },
                    },
                    # Final CTA
                    {
                        "type": "cta",
                        "data": {
                            "text": "Ready to Dive? Contact Us Today!",
                            "url": "/contact/",
                        },
                    },
                ],
            },
            {
                "slug": "courses",
                "title": "PADI Dive Courses",
                "access_level": AccessLevel.PUBLIC,
                "blocks": [
                    {
                        "type": "heading",
                        "data": {"text": "Learn to Dive with Happy Diving", "level": 1},
                    },
                    {
                        "type": "rich_text",
                        "data": {
                            "content": "<p>We offer the complete range of PADI certification courses, taught by experienced instructors in the warm, crystal-clear waters of the Caribbean. Small class sizes ensure you get the personal attention you deserve.</p>",
                        },
                    },
                    {
                        "type": "heading",
                        "data": {"text": "Beginner Courses", "level": 2},
                    },
                    {
                        "type": "rich_text",
                        "data": {
                            "content": """<ul>
<li><strong>Discover Scuba Diving</strong> - Try diving for the first time with a half-day introduction</li>
<li><strong>PADI Open Water Diver</strong> - Your first certification, dive to 18 meters worldwide</li>
<li><strong>PADI Scuba Diver</strong> - A shorter certification perfect for vacation divers</li>
</ul>""",
                        },
                    },
                    {
                        "type": "heading",
                        "data": {"text": "Continuing Education", "level": 2},
                    },
                    {
                        "type": "rich_text",
                        "data": {
                            "content": """<ul>
<li><strong>Advanced Open Water</strong> - Explore deep diving, navigation, and specialty skills</li>
<li><strong>Rescue Diver</strong> - Learn emergency response and become a safer diver</li>
<li><strong>Specialty Courses</strong> - Night diving, drift diving, underwater photography, and more</li>
</ul>""",
                        },
                    },
                    {
                        "type": "cta",
                        "data": {
                            "text": "Ask About Course Availability",
                            "url": "/contact/",
                        },
                    },
                ],
            },
            {
                "slug": "about",
                "title": "About Happy Diving",
                "access_level": AccessLevel.PUBLIC,
                "blocks": [
                    {
                        "type": "heading",
                        "data": {"text": "Our Story", "level": 1},
                    },
                    {
                        "type": "rich_text",
                        "data": {
                            "content": "<p>Happy Diving began as a dream shared by passionate divers who fell in love with the Riviera Maya's incredible underwater world. Today, we're proud to share that passion with divers from around the globe.</p><p>Based in beautiful Playa del Carmen, we have easy access to the Mesoamerican Barrier Reef, the mysterious cenotes of the Yucatan, and world-class dive sites around Cozumel.</p>",
                        },
                    },
                    {
                        "type": "heading",
                        "data": {"text": "Our Team", "level": 2},
                    },
                    {
                        "type": "rich_text",
                        "data": {
                            "content": "<p>Every member of our team is a certified PADI professional with extensive local knowledge. We're committed to safety, environmental responsibility, and making sure every diver leaves with a smile.</p><p>We speak English, Spanish, and several other languages to make international guests feel at home.</p>",
                        },
                    },
                    {
                        "type": "heading",
                        "data": {"text": "Our Commitment", "level": 2},
                    },
                    {
                        "type": "rich_text",
                        "data": {
                            "content": "<ul><li><strong>Safety First</strong> - Regularly maintained equipment and conservative dive planning</li><li><strong>Small Groups</strong> - Maximum 4-6 divers per guide</li><li><strong>Ocean Conservation</strong> - We practice and teach reef-safe diving</li><li><strong>Personal Service</strong> - Every diver's needs are important to us</li></ul>",
                        },
                    },
                ],
            },
            {
                "slug": "contact",
                "title": "Contact Happy Diving",
                "access_level": AccessLevel.PUBLIC,
                "blocks": [
                    {
                        "type": "heading",
                        "data": {"text": "Get in Touch", "level": 1},
                    },
                    {
                        "type": "rich_text",
                        "data": {
                            "content": """<p>Ready to plan your diving adventure? We'd love to hear from you!</p>
<p><strong>Location:</strong> Playa del Carmen, Quintana Roo, Mexico</p>
<p><strong>Phone:</strong> <a href="tel:+529841234567">+52 984 123 4567</a></p>
<p><strong>WhatsApp:</strong> <a href="https://wa.me/529841234567">+52 984 123 4567</a></p>
<p><strong>Email:</strong> <a href="mailto:info@happydiving.mx">info@happydiving.mx</a></p>
<p><strong>Hours:</strong> Daily 7:00 AM - 6:00 PM</p>""",
                        },
                    },
                    {
                        "type": "divider",
                        "data": {},
                    },
                    {
                        "type": "heading",
                        "data": {"text": "How to Find Us", "level": 2},
                    },
                    {
                        "type": "rich_text",
                        "data": {
                            "content": "<p>We're located in the heart of Playa del Carmen, just a short walk from the beach and 5th Avenue. Hotel pickup is available for all diving excursions.</p>",
                        },
                    },
                    {
                        "type": "cta",
                        "data": {
                            "text": "Send Us a Message",
                            "url": "mailto:info@happydiving.mx",
                        },
                    },
                ],
            },
        ]

        for config in pages_config:
            slug = config["slug"]

            existing = ContentPage.objects.filter(slug=slug, deleted_at__isnull=True).first()

            if existing:
                if options["force"]:
                    existing.delete()
                    self.stdout.write(f"  Deleted existing page: {slug}")
                else:
                    self.stdout.write(f"  Skipping existing page: {slug}")
                    continue

            page = create_page(
                slug=slug,
                title=config["title"],
                user=admin_user,
                access_level=config["access_level"],
            )

            for block_config in config["blocks"]:
                add_block(page, block_config["type"], block_config["data"])

            publish_page(page, admin_user)

            self.stdout.write(self.style.SUCCESS(f"  Created and published: {slug}"))

        self.stdout.write(self.style.SUCCESS("\nCMS seed complete!"))
