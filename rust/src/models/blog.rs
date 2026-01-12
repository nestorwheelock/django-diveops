//! Blog post models

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use uuid::Uuid;

/// Blog post for listing view
#[derive(Debug, Clone, FromRow, Serialize)]
pub struct BlogPostSummary {
    pub slug: String,
    pub title: String,
    pub excerpt: String,
    pub featured_image_url: Option<String>,
    pub category_name: Option<String>,
    pub category_slug: Option<String>,
    pub category_color: Option<String>,
    pub published_at: Option<DateTime<Utc>>,
    pub reading_time_minutes: Option<i32>,
}

/// Blog category
#[derive(Debug, Clone, FromRow, Serialize)]
pub struct BlogCategory {
    pub id: Uuid,
    pub name: String,
    pub slug: String,
    pub description: String,
    pub color: String,
    pub sort_order: i32,
}

/// Full blog post with content
#[derive(Debug, Clone, Serialize)]
pub struct BlogPostDetail {
    pub slug: String,
    pub title: String,
    pub excerpt: String,
    pub featured_image_url: Option<String>,
    pub category: Option<BlogCategory>,
    pub published_at: Option<DateTime<Utc>>,
    pub reading_time_minutes: Option<i32>,
    pub tags: Vec<String>,
    pub seo_title: String,
    pub seo_description: String,
    pub og_image_url: String,
    pub blocks: Vec<Block>,
}

/// Content block within a page
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Block {
    pub id: String,
    #[serde(rename = "type")]
    pub block_type: String,
    pub sequence: i32,
    pub data: serde_json::Value,
}

impl Block {
    /// Get the content for rich_text blocks
    pub fn content(&self) -> &str {
        self.data
            .get("content")
            .and_then(|v| v.as_str())
            .unwrap_or("")
    }

    /// Get the text for heading blocks
    pub fn text(&self) -> &str {
        self.data
            .get("text")
            .and_then(|v| v.as_str())
            .unwrap_or("")
    }

    /// Get the URL for image/embed blocks
    pub fn url(&self) -> &str {
        self.data
            .get("url")
            .and_then(|v| v.as_str())
            .unwrap_or("")
    }

    /// Get the alt text for image blocks
    pub fn alt(&self) -> &str {
        self.data
            .get("alt")
            .and_then(|v| v.as_str())
            .unwrap_or("")
    }

    /// Get the caption for image blocks
    pub fn caption(&self) -> &str {
        self.data
            .get("caption")
            .and_then(|v| v.as_str())
            .unwrap_or("")
    }

    /// Get the heading level (defaults to 2)
    pub fn level(&self) -> i64 {
        self.data
            .get("level")
            .and_then(|v| v.as_i64())
            .unwrap_or(2)
    }
}

/// Published snapshot structure (matches Django's format)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PublishedSnapshot {
    pub version: i32,
    pub published_at: String,
    pub published_by_id: Option<String>,
    pub checksum: Option<String>,
    pub meta: PageMeta,
    #[serde(default)]
    pub blocks: Vec<Block>,
}

/// Page metadata from snapshot
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PageMeta {
    pub title: String,
    pub slug: String,
    #[serde(default)]
    pub path: String,
    #[serde(default)]
    pub seo_title: String,
    #[serde(default)]
    pub seo_description: String,
    #[serde(default)]
    pub og_image_url: String,
    #[serde(default = "default_robots")]
    pub robots: String,
}

fn default_robots() -> String {
    "index, follow".to_string()
}
