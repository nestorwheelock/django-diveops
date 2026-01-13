//! App download page route handler

use askama::Template;
use axum::response::Html;
use base64::{engine::general_purpose::STANDARD, Engine};
use image::{ImageBuffer, Luma};
use qrcode::QrCode;
use std::cmp::Ordering;
use std::fs;
use std::io::Cursor;
use std::path::Path;

use crate::error::Result;

/// Semantic version for APK files (supports suffixes like -alpha, -beta, -rc1)
#[derive(Debug, Clone, Eq, PartialEq)]
struct Version {
    major: u32,
    minor: u32,
    patch: u32,
    suffix: Option<String>,
}

impl Version {
    fn parse(s: &str) -> Option<Version> {
        // Handle versions like "0.1.0-alpha" or "1.0.0"
        let (version_part, suffix) = if let Some(idx) = s.find('-') {
            (&s[..idx], Some(s[idx + 1..].to_string()))
        } else {
            (s, None)
        };

        let parts: Vec<&str> = version_part.split('.').collect();
        if parts.len() != 3 {
            return None;
        }
        Some(Version {
            major: parts[0].parse().ok()?,
            minor: parts[1].parse().ok()?,
            patch: parts[2].parse().ok()?,
            suffix,
        })
    }
}

impl Ord for Version {
    fn cmp(&self, other: &Self) -> Ordering {
        match self.major.cmp(&other.major) {
            Ordering::Equal => match self.minor.cmp(&other.minor) {
                Ordering::Equal => match self.patch.cmp(&other.patch) {
                    Ordering::Equal => {
                        // Versions with suffix come before versions without (alpha < release)
                        match (&self.suffix, &other.suffix) {
                            (None, None) => Ordering::Equal,
                            (Some(_), None) => Ordering::Less,
                            (None, Some(_)) => Ordering::Greater,
                            (Some(a), Some(b)) => a.cmp(b),
                        }
                    }
                    o => o,
                },
                o => o,
            },
            o => o,
        }
    }
}

impl PartialOrd for Version {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl std::fmt::Display for Version {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match &self.suffix {
            Some(s) => write!(f, "{}.{}.{}-{}", self.major, self.minor, self.patch, s),
            None => write!(f, "{}.{}.{}", self.major, self.minor, self.patch),
        }
    }
}

/// APK file info
#[derive(Debug)]
struct ApkInfo {
    filename: String,
    version: Version,
}

/// Download page template
#[derive(Template)]
#[template(path = "app/download.html")]
struct DownloadTemplate {
    has_apk: bool,
    version: String,
    filename: String,
    download_url: String,
    qr_code_data: String,
}

/// Find the latest APK in the downloads directory
fn find_latest_apk() -> Option<ApkInfo> {
    let downloads_dir = Path::new("static/downloads");

    if !downloads_dir.exists() {
        tracing::warn!("Downloads directory does not exist: {:?}", downloads_dir);
        return None;
    }

    let mut apks: Vec<ApkInfo> = fs::read_dir(downloads_dir)
        .ok()?
        .filter_map(|entry| {
            let entry = entry.ok()?;
            let filename = entry.file_name().to_string_lossy().to_string();

            // Match pattern: buceo-X.Y.Z.apk or buceo-X.Y.Z-suffix.apk
            if filename.starts_with("buceo-") && filename.ends_with(".apk") {
                let version_str = filename
                    .strip_prefix("buceo-")?
                    .strip_suffix(".apk")?;
                let version = Version::parse(version_str)?;
                Some(ApkInfo { filename, version })
            } else {
                None
            }
        })
        .collect();

    // Sort by version descending, take the latest
    apks.sort_by(|a, b| b.version.cmp(&a.version));
    apks.into_iter().next()
}

/// Generate QR code as base64 PNG data URI
fn generate_qr_code(url: &str) -> String {
    let code = match QrCode::new(url.as_bytes()) {
        Ok(c) => c,
        Err(e) => {
            tracing::error!("Failed to create QR code: {}", e);
            return String::new();
        }
    };

    // Render to image
    let image = code.render::<Luma<u8>>().quiet_zone(true).build();

    // Scale up for better visibility (4x)
    let width = image.width() * 4;
    let height = image.height() * 4;
    let scaled: ImageBuffer<Luma<u8>, Vec<u8>> = image::imageops::resize(
        &image,
        width,
        height,
        image::imageops::FilterType::Nearest,
    );

    // Encode as PNG
    let mut png_bytes = Cursor::new(Vec::new());
    if let Err(e) = scaled.write_to(&mut png_bytes, image::ImageFormat::Png) {
        tracing::error!("Failed to encode QR code as PNG: {}", e);
        return String::new();
    }

    // Convert to base64 data URI
    let base64_data = STANDARD.encode(png_bytes.get_ref());
    format!("data:image/png;base64,{}", base64_data)
}

/// App download page handler
pub async fn download() -> Result<Html<String>> {
    let base_url = std::env::var("BASE_URL").unwrap_or_else(|_| "https://happydiving.mx".to_string());

    let (has_apk, version, filename, download_url, qr_code_data) = match find_latest_apk() {
        Some(apk) => {
            let download_url = format!("{}/static/downloads/{}", base_url, apk.filename);
            let qr_code_data = generate_qr_code(&download_url);
            (true, apk.version.to_string(), apk.filename, download_url, qr_code_data)
        }
        None => {
            tracing::info!("No APK files found in downloads directory");
            (false, String::new(), String::new(), String::new(), String::new())
        }
    };

    let template = DownloadTemplate {
        has_apk,
        version,
        filename,
        download_url,
        qr_code_data,
    };

    Ok(Html(template.render().unwrap()))
}
