use std::fs::{self};
use std::io::{Read, Write};
use std::path::Path;

use flate2::{Compression, write::DeflateEncoder, read::DeflateDecoder};
use sha2::{Sha256, Digest};
use tar::{Builder, Archive};

const VERSION: &str = "2.1";

// ============================================================
// BRAILLE
// ============================================================

fn bytes_to_braille(bytes: &[u8]) -> String {
    bytes.iter()
        .map(|b| char::from_u32(0x2800 + *b as u32).expect("valid braille codepoint"))
        .collect()
}

fn braille_to_bytes(s: &str) -> Result<Vec<u8>, String> {
    let mut out = Vec::with_capacity(s.chars().count());
    for (i, c) in s.chars().enumerate() {
        let code = c as u32;
        if !(0x2800..=0x28FF).contains(&code) {
            return Err(format!("invalid braille glyph at char index {}", i));
        }
        out.push((code - 0x2800) as u8);
    }
    Ok(out)
}

// ============================================================
// TAR
// ============================================================

fn build_tar(input_path: &str) -> Result<Vec<u8>, String> {
    let mut tar_data = Vec::new();
    {
        let mut builder = Builder::new(&mut tar_data);
        let path = Path::new(input_path);

        if !path.exists() {
            return Err(format!("input path does not exist: {}", input_path));
        }

        if path.is_dir() {
            builder
                .append_dir_all(".", path)
                .map_err(|e| format!("failed to append directory: {e}"))?;
        } else {
            builder
                .append_path(path)
                .map_err(|e| format!("failed to append file: {e}"))?;
        }

        builder
            .finish()
            .map_err(|e| format!("failed to finalize tar: {e}"))?;
    }
    Ok(tar_data)
}

fn extract_tar(bytes: &[u8], output_dir: &str) -> Result<(), String> {
    fs::create_dir_all(output_dir)
        .map_err(|e| format!("failed to create output dir: {e}"))?;
    let mut archive = Archive::new(bytes);
    archive
        .unpack(output_dir)
        .map_err(|e| format!("failed to unpack tar: {e}"))
}

// ============================================================
// HASH
// ============================================================

fn sha256(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    let result = hasher.finalize();
    hex::encode(result)
}

// ============================================================
// DEFLATE
// ============================================================

fn deflate(data: &[u8]) -> Result<Vec<u8>, String> {
    let mut encoder = DeflateEncoder::new(Vec::new(), Compression::best());
    encoder
        .write_all(data)
        .map_err(|e| format!("deflate write failed: {e}"))?;
    encoder
        .finish()
        .map_err(|e| format!("deflate finalize failed: {e}"))
}

fn inflate(data: &[u8]) -> Result<Vec<u8>, String> {
    let mut decoder = DeflateDecoder::new(data);
    let mut out = Vec::new();
    decoder
        .read_to_end(&mut out)
        .map_err(|e| format!("inflate failed: {e}"))?;
    Ok(out)
}

// ============================================================
// SIGIL PARSE
// ============================================================

fn parse_sigil(sigil: &str) -> Result<(String, usize, String, String), String> {
    let trimmed = sigil.trim();
    let mut parts = trimmed.splitn(4, ':');

    let header = parts.next().ok_or("missing header")?;
    let len_str = parts.next().ok_or("missing tar length")?;
    let hash = parts.next().ok_or("missing sha256")?;
    let glyphs = parts.next().ok_or("missing glyph payload")?;

    let version = header
        .strip_prefix("GLYPH_SIGIL_v")
        .ok_or("invalid header prefix")?
        .to_string();

    let expected_len = len_str
        .parse::<usize>()
        .map_err(|e| format!("invalid tar length: {e}"))?;

    if hash.len() != 64 || !hash.chars().all(|c| c.is_ascii_hexdigit()) {
        return Err("invalid sha256 field".to_string());
    }

    Ok((version, expected_len, hash.to_lowercase(), glyphs.to_string()))
}

// ============================================================
// ENCODE
// ============================================================

fn encode(input: &str, output: &str) -> Result<(), String> {
    let tar = build_tar(input)?;
    let hash = sha256(&tar);
    let compressed = deflate(&tar)?;
    let glyphs = bytes_to_braille(&compressed);

    let sigil = format!(
        "GLYPH_SIGIL_v{}:{}:{}:{}",
        VERSION,
        tar.len(),
        hash,
        glyphs
    );

    fs::write(output, sigil).map_err(|e| format!("failed to write output sigil: {e}"))?;
    println!("encoded -> {}", output);
    Ok(())
}

// ============================================================
// DECODE
// ============================================================

fn decode(input: &str, output_dir: &str) -> Result<(), String> {
    let sigil = fs::read_to_string(input).map_err(|e| format!("failed to read sigil: {e}"))?;
    let (version, expected_len, expected_hash, glyphs) = parse_sigil(&sigil)?;

    if version != VERSION {
        eprintln!(
            "warning: sigil version {} does not match engine version {}",
            version, VERSION
        );
    }

    let compressed = braille_to_bytes(&glyphs)?;
    let tar = inflate(&compressed)?;

    if tar.len() != expected_len {
        return Err(format!(
            "length mismatch: expected {}, got {}",
            expected_len,
            tar.len()
        ));
    }

    let actual_hash = sha256(&tar);
    if actual_hash != expected_hash {
        return Err(format!(
            "sha256 mismatch: expected {}, got {}",
            expected_hash, actual_hash
        ));
    }

    extract_tar(&tar, output_dir)?;
    println!("decoded -> {}", output_dir);
    Ok(())
}

// ============================================================
// CLI
// ============================================================

fn print_usage() {
    eprintln!("Usage:");
    eprintln!("  glyphmatics encode <input_path> <output.sigil>");
    eprintln!("  glyphmatics decode <input.sigil> <output_dir>");
}

fn main() {
    let args: Vec<String> = std::env::args().collect();

    if args.len() != 4 {
        print_usage();
        std::process::exit(1);
    }

    let result = match args[1].as_str() {
        "encode" => encode(&args[2], &args[3]),
        "decode" => decode(&args[2], &args[3]),
        _ => {
            print_usage();
            std::process::exit(1);
        }
    };

    if let Err(err) = result {
        eprintln!("error: {}", err);
        std::process::exit(1);
    }
}
