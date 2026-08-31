from pathlib import Path
from PIL import Image, ImageDraw

from packages.analysis import analyze_video_file


def _make_video(path: Path) -> None:
    frames = []
    for text in ['TOOLS', 'SAFETY', 'REPAIR']:
        image = Image.new('RGB', (320, 240), 'black')
        draw = ImageDraw.Draw(image)
        draw.text((30, 120), text, fill='white')
        frames.append(image)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=1000, loop=0)


def test_analyze_video_file_extracts_claims(tmp_path: Path) -> None:
    video_path = tmp_path / 'sample.gif'
    _make_video(video_path)
    result = analyze_video_file(
        tenant_id='tenant-1',
        agent_id='agent-1',
        agent_version_id='agent-version-1',
        source_id='source-1',
        source_revision_id='revision-1',
        source_fingerprint_sha256='fingerprint-1',
        source_type='uploaded_media',
        authority_class='owned_media',
        objective_id='objective-1',
        objective_type='comprehensive_summary',
        job_id='job-1',
        video_path=video_path,
        transcript='TOOLS SAFETY REPAIR',
    )
    assert result.claims
    assert 'tools' in result.summary.lower()
    assert result.receipt_payload.qualified in {True, False}
    assert result.receipt_signature.value
