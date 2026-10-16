"""Encode the actual pipeline browser recording as a silent H.264 MP4."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.logs/pipeline-video'


def timestamp(seconds):
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3600000)
    minutes, milliseconds = divmod(milliseconds, 60000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return f'{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}'


def main():
    result = json.loads((WORK / 'recording-result.json').read_text())
    status = json.loads((WORK / 'status.json').read_text(encoding='utf-8-sig'))
    assert result['conclusion'] == 'success' and result['source_sha'] == status['run']['head_sha']
    assert len(status['jobs']) == 3 and all(job['conclusion'] == 'success' for job in status['jobs'])
    recordings = list((WORK / 'raw').glob('*.webm'))
    if len(recordings) != 1 or recordings[0].stat().st_size == 0:
        raise RuntimeError('Expected one completed raw recording; preserve separate recording sessions')
    duration = imageio_ffmpeg.read_frames(str(recordings[0]))
    try:
        metadata = next(duration)
    finally:
        duration.close()
    seconds = metadata['duration']
    timeline = result['timeline']
    srt = []
    chapters = [';FFMETADATA1', 'title=StockFlow - Working GitHub Actions pipeline (silent)', 'comment=Actual run: ' + result['run_url']]
    for index, entry in enumerate(timeline):
        start = entry['seconds']
        end = timeline[index + 1]['seconds'] if index + 1 < len(timeline) else seconds
        if end <= start:
            continue
        srt.append(f'{len(srt) + 1}\n{timestamp(start)} --> {timestamp(end)}\n{entry["chapter"]}\n')
        title = entry['chapter'].replace('=', '-').replace('\n', ' ')
        chapters += ['[CHAPTER]', 'TIMEBASE=1/1000', f'START={int(start * 1000)}', f'END={int(end * 1000)}', 'title=' + title]
    subtitles = ROOT / 'demo/stockflow-pipeline-silent.srt'
    subtitles.write_text('\n'.join(srt), encoding='utf-8')
    chapter_file = WORK / 'chapters.ffmetadata'
    chapter_file.write_text('\n'.join(chapters) + '\n', encoding='utf-8')
    output = ROOT / 'demo/stockflow-pipeline-silent.mp4'
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [ffmpeg, '-hide_banner', '-y', '-i', str(recordings[0]), '-i', str(chapter_file), '-i', str(subtitles), '-map', '0:v:0', '-map', '2:s:0', '-map_metadata', '1', '-map_chapters', '1', '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-pix_fmt', 'yuv420p', '-c:s', 'mov_text', '-an', '-movflags', '+faststart', str(output)]
    with (WORK / 'encoding.log').open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    check = subprocess.run([ffmpeg, '-hide_banner', '-i', str(output), '-map', '0:v:0', '-f', 'null', '-'], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=True)
    if 'Audio:' in check.stderr:
        raise RuntimeError('The narration-ready video must have no audio track')
    samples = [5, 18, 55, min(90, seconds / 2), seconds / 2, seconds - 60, seconds - 38, seconds - 10]
    for index, sample in enumerate(samples):
        subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(max(0, sample)), '-i', str(output), '-frames:v', '1', str(WORK / f'qa-{index + 1:02}.png')], check=True)
    proof = {'recorded_on': '2026-10-16', 'encoded_at_utc': datetime.now(timezone.utc).isoformat(), 'run_url': result['run_url'], 'source_sha': result['source_sha'], 'conclusion': 'success', 'silent': True, 'audio_tracks': 0, 'duration_seconds': seconds, 'resolution': metadata['size'], 'video_codec': 'H.264', 'file': 'demo/stockflow-pipeline-silent.mp4', 'bytes': output.stat().st_size, 'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'actual_git_push_captured': True, 'all_three_jobs_succeeded': True, 'scope': 'CI/CD pipeline chapter; other capstone modules are separate', 'chapters': timeline}
    (ROOT / 'demo/PIPELINE_VIDEO_VERIFICATION.json').write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps({key: value for key, value in proof.items() if key != 'chapters'}, indent=2))


if __name__ == '__main__':
    main()
