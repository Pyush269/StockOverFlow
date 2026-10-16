"""Assemble the required silent capstone sections from actual project evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.logs/walkthrough'
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def media(path):
    frames = imageio_ffmpeg.read_frames(str(path))
    try:
        return next(frames)
    finally:
        frames.close()


def encode(name, arguments):
    output = WORK / (name + '.mp4')
    command = [FFMPEG, '-hide_banner', '-y'] + arguments + ['-an', '-vf', 'fps=25,scale=1600:900:force_original_aspect_ratio=decrease,pad=1600:900:(ow-iw)/2:(oh-ih)/2,setsar=1', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24', '-pix_fmt', 'yuv420p', '-threads', '2', '-movflags', '+faststart', str(output)]
    with (WORK / (name + '-encode.log')).open('w') as log:
        subprocess.run(command, stdout=log, stderr=log, check=True)
    print('Encoded ' + name, flush=True)
    return output


def clock(seconds, separator=','):
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3600000)
    minutes, milliseconds = divmod(milliseconds, 60000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return f'{hours:02}:{minutes:02}:{seconds:02}{separator}{milliseconds:03}'


def main():
    recording = json.loads((WORK / 'recording.json').read_text())
    assert len(recording['segments']) == 2
    assert not any('missing_required_console_capture' in check for check in recording['checks']), 'Actual AWS Console captures are required'
    for name in ['stockflow-aws-eks-console.png', 'stockflow-aws-vpc-console.png']:
        assert (ROOT / 'docs/screenshots' / name).is_file()
    pipeline = json.loads((ROOT / 'demo/PIPELINE_VIDEO_VERIFICATION.json').read_text())
    original = ROOT / pipeline['file']
    assert pipeline['conclusion'] == 'success'
    assert hashlib.sha256(original.read_bytes()).hexdigest() == pipeline['sha256']
    slide_files = sorted((WORK / 'slides').glob('slide-*.png'))
    assert len(slide_files) == 11
    slide_list = WORK / 'slides.concat'
    rows = []
    for file in slide_files:
        rows += [f"file '{file.as_posix()}'", 'duration 10']
    rows += [f"file '{slide_files[-1].as_posix()}'"]
    slide_list.write_text('\n'.join(rows) + '\n')
    slides = encode('slides', ['-f', 'concat', '-safe', '0', '-i', str(slide_list), '-t', '110'])
    application = encode('application-code', ['-i', str(ROOT / recording['segments'][0]['video'])])
    # Keep the real push, live progress, completed run, and actual job output.
    # Remove the optional introductory cards and repeated concluding card.
    ci_start, ci_end = 50, 354
    ci = encode('ci-required', ['-ss', str(ci_start), '-i', str(original), '-t', str(ci_end - ci_start)])
    operations = encode('operations', ['-i', str(ROOT / recording['segments'][1]['video'])])
    parts = [slides, application, ci, operations]
    durations = [media(part)['duration'] for part in parts]
    chapters = [{'seconds': 0, 'title': 'Slides: project and architecture', 'caption': '11 project slides, including stack, architecture, CI, AWS, Kubernetes, and observability.'}]
    for item in recording['segments'][0]['chapters']:
        chapters.append(dict(item, seconds=durations[0] + item['seconds']))
    offset = durations[0] + durations[1]
    for item in pipeline['chapters']:
        if ci_start <= item['seconds'] < ci_end:
            chapters.append({'seconds': offset + item['seconds'] - ci_start, 'title': item['chapter'], 'caption': item['note']})
    offset += durations[2]
    for item in recording['segments'][1]['chapters']:
        chapters.append(dict(item, seconds=offset + item['seconds']))
    chapters.sort(key=lambda c: c['seconds'])
    total = sum(durations)
    subtitle_rows, metadata = [], [';FFMETADATA1', 'title=StockFlow - Required capstone walkthrough (silent)', 'comment=Actual AWS deployment and GitHub Actions evidence. No narration.']
    for index, chapter in enumerate(chapters):
        end = chapters[index + 1]['seconds'] if index + 1 < len(chapters) else total
        title = chapter['title'].replace('=', '-').replace('\n', ' ')
        metadata += ['[CHAPTER]', 'TIMEBASE=1/1000', f'START={round(chapter["seconds"] * 1000)}', f'END={round(end * 1000)}', 'title=' + title]
        subtitle_rows.append(f'{index + 1}\n{clock(chapter["seconds"])} --> {clock(end)}\n{chapter["title"]}\n{chapter["caption"]}\n')
    srt = ROOT / 'demo/stockflow-walkthrough-silent.srt'
    srt.write_text('\n'.join(subtitle_rows), encoding='utf-8')
    chapter_file = WORK / 'chapters.ffmetadata'
    chapter_file.write_text('\n'.join(metadata) + '\n', encoding='utf-8')
    concat = WORK / 'video.concat'
    concat.write_text('\n'.join(f"file '{p.as_posix()}'" for p in parts) + '\n')
    output = ROOT / 'demo/stockflow-walkthrough-silent.mp4'
    subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat), '-i', str(chapter_file), '-i', str(srt), '-map', '0:v:0', '-map', '2:s:0', '-map_metadata', '1', '-map_chapters', '1', '-c:v', 'copy', '-c:s', 'mov_text', '-an', '-movflags', '+faststart', str(output)], check=True)
    result = subprocess.run([FFMPEG, '-hide_banner', '-i', str(output), '-map', '0:v:0', '-f', 'null', '-'], capture_output=True, text=True, check=True)
    assert 'Audio:' not in result.stderr
    assert not any(term in result.stderr.lower() for term in ['non monotonically', 'invalid data', 'error while decoding'])
    actual = media(output)
    assert abs(actual['duration'] - total) < 2
    report = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'file': str(output.relative_to(ROOT)).replace('\\', '/'), 'silent': True, 'audio_tracks': 0, 'duration_seconds': actual['duration'], 'resolution': actual['size'], 'bytes': output.stat().st_size, 'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'full_video_decode': 'passed', 'scope': 'Required capstone walkthrough: slides, code, actual push/CI, Terraform/AWS Console, ArgoCD, Kubernetes, Prometheus Targets, Grafana', 'ci_run_url': pipeline['run_url'], 'ci_source_sha': pipeline['source_sha'], 'ci_excerpt_seconds': [ci_start, ci_end], 'cloud_recorded_at_utc': recording['recorded_at_utc'], 'checks': recording['checks'], 'chapters': chapters}
    (ROOT / 'demo/WALKTHROUGH_VERIFICATION.json').write_text(json.dumps(report, indent=2) + '\n')
    guide = ['# Silent capstone walkthrough', '', '[Watch/download the complete MP4](stockflow-walkthrough-silent.mp4).', '', 'No narration is needed. On-screen explanations and selectable captions describe the actual project evidence.', '', f'Duration: {clock(actual["duration"], ".")}. Resolution: 1600 x 900. No audio track.', '', '## Chapters', '']
    for chapter in chapters:
        guide.append(f'- **{clock(chapter["seconds"], ".")[:-4]}** — {chapter["title"]}')
    guide += ['', 'The pipeline section is the actual successful push-triggered run linked in the verification report. It ends at GHCR publication; the separate ArgoCD section explains how a Git values commit controls deployment.', '', 'AWS Console images are actual captured project screens. Command cards display real captured output and source excerpts. Optional installation, load, and recovery demonstrations are omitted.', '', 'After evaluation, perform and verify AWS cleanup and save destroy evidence. Cleanup has not yet been performed.']
    (ROOT / 'demo/WALKTHROUGH.md').write_text('\n'.join(guide) + '\n', encoding='utf-8')
    for index, seconds in enumerate([5, 105, durations[0] + 8, offset - durations[2] + 5, offset + 3, offset + 24, total - 45, total - 12]):
        subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(max(0, seconds)), '-i', str(output), '-frames:v', '1', str(WORK / f'qa-final-{index + 1:02}.png')], check=True)
    print(json.dumps({k: v for k, v in report.items() if k not in ['chapters', 'checks']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
