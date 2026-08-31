use std::fs::{self, File};
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
    bytes.iter().map(|b| char::from_u32(0x2800 + *b as u32).unwrap()).collect()
}

fn braille_to_bytes(s: &str) -> Vec<u8> {
    s.chars().map(|c| (c as u32 - 0x2800) as u8).collect()
}

// ============================================================
// TAR
// ============================================================

fn build_tar(input_path: &str) -> Vec<u8> {
    let mut tar_data = Vec::new();
    let mut builder = Builder::new(&mut tar_data);

    if Path::new(input_path).is_dir() {
        builder.append_dir_all(".", input_path).unwrap();
    } else {
        builder.append_path(input_path).unwrap();
    }

    builder.finish().unwrap();
    tar_data
}

fn extract_tar(bytes: &[u8], output_dir: &str) {
    let mut archive = Archive::new(bytes);
    archive.unpack(output_dir).unwrap();
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

fn deflate(data: &[u8]) -> Vec<u8> {
    let mut encoder = DeflateEncoder::new(Vec::new(), Compression::best());
    encoder.write_all(data).unwrap();
    encoder.finish().unwrap()
}

fn inflate(data: &[u8]) -> Vec<u8> {
    let mut decoder = DeflateDecoder::new(data);
    let mut out = Vec::new();
    decoder.read_to_end(&mut out).unwrap();
    out
}

// ============================================================
// ENCODE
// ============================================================

fn encode(input: &str, output: &str) {
    let tar = build_tar(input);
    let hash = sha256(&tar);
    let compressed = deflate(&tar);
    let glyphs = bytes_to_braille(&compressed);

    let sigil = format!(
        "GLYPH_SIGIL_v{}:{}:{}:{}",
        VERSION,
        tar.len(),
        hash,
        glyphs
    );

    fs::write(output, sigil).unwrap();
    println!("✔ Encoded → {}", output);
}

// ============================================================
// DECODE
// ============================================================

fn decode(input: &str, output_dir: &str) {
    let sigil = fs::read_to_string(input).unwrap();

    let parts: Vec<&str> = sigil.splitn(4, ':').collect();
    if parts.len() != 4 {
        panic!("Invalid sigil format");
    }

    let expected_len: usize = parts[1].parse().unwrap();
    let expected_hash = parts[2];
    let glyphs = parts[3];

    let compressed = braille_to_bytes(glyphs);
    let tar = inflate(&compressed);

    if tar.len() != expected_len {
        panic!("Length mismatch");
    }

    let actual_hash = sha256(&tar);
    if actual_hash != expected_hash {
        panic!("SHA256 mismatch");
    }

    extract_tar(&tar, output_dir);

    println!("✔ Decoded → {}", output_dir);
}

// ============================================================
// CLI
// ============================================================

fn main() {
    let args: Vec<String> = std::env::args().collect();

    if args.len() < 4 {
        println!("Usage:");
        println!("  encode <input_path> <output.sigil>");
        println!("  decode <input.sigil> <output_dir>");
        return;
    }

    match args[1].as_str() {
        "encode" => encode(&args[2], &args[3]),
        "decode" => decode(&args[2], &args[3]),
        _ => println!("Unknown command"),
    }
}
