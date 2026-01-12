"""Management command to import Facebook posts as blog content."""

import re
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.utils import timezone

from django_cms_core.models import (
    BlogCategory,
    ContentPage,
    AccessLevel,
    PageStatus,
    PageType,
)
from django_cms_core.services import add_block, publish_page
from django_parties.models import Person


User = get_user_model()


def generate_slug(text, date_str):
    """Generate a URL-safe slug from post text and date."""
    # Take first 50 chars, remove special chars
    clean = re.sub(r'[^\w\s-]', '', text[:50].lower())
    words = clean.split()[:6]  # First 6 words
    base_slug = slugify('-'.join(words))
    # Add date prefix for uniqueness
    return f"{date_str}-{base_slug}" if base_slug else f"{date_str}-post"


def estimate_reading_time(text):
    """Estimate reading time in minutes (200 words per minute)."""
    word_count = len(text.split())
    return max(1, round(word_count / 200))


def generate_excerpt(text, max_length=200):
    """Generate excerpt from post text."""
    # Clean up the text
    clean = text.replace('\n', ' ').replace('  ', ' ').strip()
    if len(clean) <= max_length:
        return clean
    # Find last space before max_length - 3 (for ellipsis)
    excerpt = clean[:max_length - 3]
    last_space = excerpt.rfind(' ')
    if last_space > 0:
        excerpt = excerpt[:last_space]
    result = excerpt + '...'
    # Final safety check
    return result[:max_length]


def categorize_post(text):
    """Auto-categorize post based on content keywords."""
    text_lower = text.lower()

    if any(word in text_lower for word in ['certification', 'course', 'student', 'training', 'padi', 'open water', 'taught']):
        return 'training'
    elif any(word in text_lower for word in ['turtle', 'ray', 'fish', 'moray', 'octopus', 'puffer', 'barracuda', 'coral']):
        return 'marine-life'
    elif any(word in text_lower for word in ['gear', 'wetsuit', 'regulator', 'tank', 'cylinder', 'camera', 'equipment']):
        return 'gear'
    elif any(word in text_lower for word in ['safety', 'emergency', 'rescue', 'conditions', 'flag']):
        return 'safety'
    elif any(word in text_lower for word in ['conservation', 'protect', 'sargassum', 'reef health', 'bleaching']):
        return 'conservation'
    elif any(word in text_lower for word in ['cenote', 'cozumel', 'jardines', 'parque nacional', 'puerto morelos']):
        return 'destinations'
    else:
        return 'stories'  # Default to dive stories


class Command(BaseCommand):
    help = "Import Facebook posts as blog content"

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='/home/nwheelo/Downloads/buceofeliz-posts-dated.txt',
            help='Path to the posts file',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview without creating posts',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limit number of posts to import (0 = all)',
        )
        parser.add_argument(
            '--publish',
            action='store_true',
            help='Publish posts immediately (default is draft)',
        )

    def handle(self, *args, **options):
        file_path = options['file']
        dry_run = options['dry_run']
        limit = options['limit']
        publish = options['publish']

        # Get admin user
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user and not dry_run:
            self.stdout.write(self.style.ERROR("No superuser found. Create one first."))
            return

        # Get author
        author = Person.objects.filter(deleted_at__isnull=True).first()

        # Load category map
        category_map = {}
        for cat in BlogCategory.objects.filter(deleted_at__isnull=True):
            category_map[cat.slug] = cat

        # Parse posts file
        self.stdout.write(f"\nReading posts from: {file_path}")

        try:
            with open(file_path, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        # Split by post delimiter
        raw_posts = content.split('---\ndate:')
        posts = []

        for raw in raw_posts[1:]:  # Skip first empty split
            lines = raw.strip().split('\n')
            if not lines:
                continue

            # Extract date
            date_line = lines[0].strip()
            date_str = date_line.split('---')[0].strip()

            # Extract text (everything after the second ---)
            text_start = raw.find('---\n')
            if text_start >= 0:
                text = raw[text_start + 4:].strip()
            else:
                text = '\n'.join(lines[1:]).strip()

            if text and len(text) > 30:  # Skip very short posts
                posts.append({
                    'date': date_str,
                    'text': text,
                })

        self.stdout.write(f"Found {len(posts)} posts to import\n")

        if limit > 0:
            posts = posts[:limit]
            self.stdout.write(f"Limited to {limit} posts\n")

        # Import posts
        created = 0
        skipped = 0

        for post_data in posts:
            date_str = post_data['date']
            text = post_data['text']

            # Generate slug
            slug = generate_slug(text, date_str)

            # Check if exists
            existing = ContentPage.objects.filter(
                slug=slug, deleted_at__isnull=True
            ).first()

            if existing:
                skipped += 1
                if not dry_run:
                    self.stdout.write(f"  Skipped (exists): {slug[:50]}")
                continue

            # Generate title from first sentence
            first_line = text.split('\n')[0][:100]
            if len(first_line) > 70:
                first_line = first_line[:67] + '...'
            title = first_line

            # Categorize
            cat_slug = categorize_post(text)
            category = category_map.get(cat_slug)

            # Parse date
            try:
                pub_date = datetime.strptime(date_str, '%Y-%m-%d')
                pub_date = timezone.make_aware(pub_date)
            except ValueError:
                pub_date = timezone.now()

            if dry_run:
                self.stdout.write(f"  Would create: [{date_str}] {title[:50]}... ({cat_slug})")
                created += 1
                continue

            # Create the post
            post = ContentPage.objects.create(
                slug=slug,
                title=title,
                page_type=PageType.POST,
                status=PageStatus.DRAFT,
                access_level=AccessLevel.PUBLIC,
                author=author,
                excerpt=generate_excerpt(text),
                reading_time_minutes=estimate_reading_time(text),
                category=category,
                tags=['facebook-import', 'buceo-feliz'],
                seo_title=title[:70],
                seo_description=generate_excerpt(text, 155),  # Leave room for ellipsis
                published_at=pub_date,
                metadata={'source': 'facebook', 'original_date': date_str},
            )

            # Add content as rich text block
            # Convert newlines to paragraphs
            paragraphs = text.split('\n\n')
            html_content = ''.join(f'<p>{p.strip()}</p>' for p in paragraphs if p.strip())

            add_block(post, 'rich_text', {'content': html_content})

            if publish:
                publish_page(post, admin_user)
                self.stdout.write(self.style.SUCCESS(f"  Created & published: {title[:50]}..."))
            else:
                self.stdout.write(self.style.SUCCESS(f"  Created (draft): {title[:50]}..."))

            created += 1

        self.stdout.write(f"\n{'Would create' if dry_run else 'Created'}: {created}")
        self.stdout.write(f"Skipped: {skipped}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDry run - no posts created. Run without --dry-run to import."))
