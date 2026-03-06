#!/usr/bin/env python3
"""SpeakCards - English learning video generator with TTS flashcards."""

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont


# Video settings
WIDTH = 1920
HEIGHT = 1080
BG_COLOR = (30, 30, 30)
TEXT_COLOR = (255, 255, 255)
CARD_COLOR = (50, 50, 50)
CARD_RADIUS = 30
CARD_PADDING = 80
FONT_SIZE = 64
CARD_NUMBER_SIZE = 28


def get_font(size):
    """Try to load a nice font, fall back to default."""
    font_candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ]
    for font_path in font_candidates:
        if os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)
    return ImageFont.load_default()


def create_card_image(text, index, total, output_path):
    """Create a flashcard image with the given text."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Draw card background
    card_margin = 200
    card_rect = [card_margin, card_margin, WIDTH - card_margin, HEIGHT - card_margin]
    draw.rounded_rectangle(card_rect, radius=CARD_RADIUS, fill=CARD_COLOR)

    # Draw card number
    num_font = get_font(CARD_NUMBER_SIZE)
    num_text = f"{index + 1} / {total}"
    num_bbox = draw.textbbox((0, 0), num_text, font=num_font)
    num_x = WIDTH - card_margin - CARD_PADDING - (num_bbox[2] - num_bbox[0])
    num_y = card_margin + 30
    draw.text((num_x, num_y), num_text, fill=(150, 150, 150), font=num_font)

    # Draw main text (centered in card)
    font = get_font(FONT_SIZE)
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    text_x = (WIDTH - text_w) // 2
    text_y = (HEIGHT - text_h) // 2
    draw.text((text_x, text_y), text, fill=TEXT_COLOR, font=font)

    img.save(output_path)


def create_tts_audio(text, output_path):
    """Generate TTS audio for the given text."""
    tts = gTTS(text=text, lang="en")
    tts.save(output_path)


def get_audio_duration(audio_path):
    """Get the duration of an audio file using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            audio_path,
        ],
        capture_output=True, text=True,
    )
    return float(result.stdout.strip())


SPEED_ROUNDS = [1.2, 1.0, 0.8, 0.7]


def build_video(sentences, output_path, pause_before=1.0, pause_after=1.5):
    """Build the final video from sentences."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        total = len(sentences)
        segments = []
        seg_idx = 0

        for i, sentence in enumerate(sentences):
            print(f"  [{i+1}/{total}] {sentence}")

            img_path = tmpdir / f"card_{i:03d}.png"
            audio_path = tmpdir / f"audio_{i:03d}.mp3"

            # Generate card image and TTS audio (once per sentence)
            create_card_image(sentence, i, total, str(img_path))
            create_tts_audio(sentence, str(audio_path))
            base_dur = get_audio_duration(str(audio_path))

            for round_idx, speed in enumerate(SPEED_ROUNDS):
                segment_path = tmpdir / f"segment_{seg_idx:04d}.mp4"
                adjusted_audio_path = tmpdir / f"audio_{seg_idx:04d}_speed.mp3"
                seg_idx += 1

                speed_label = f"x{speed}"
                print(f"    Round {round_idx+1}/{len(SPEED_ROUNDS)} ({speed_label})")

                # First: create speed-adjusted audio file
                subprocess.run(
                    [
                        "ffmpeg", "-y",
                        "-i", str(audio_path),
                        "-filter:a", f"atempo={speed}",
                        str(adjusted_audio_path),
                    ],
                    capture_output=True,
                )

                # Measure actual duration of adjusted audio
                adjusted_dur = get_audio_duration(str(adjusted_audio_path))
                total_dur = pause_before + adjusted_dur + pause_after

                # Create video segment with adjusted audio
                subprocess.run(
                    [
                        "ffmpeg", "-y",
                        "-loop", "1", "-i", str(img_path),
                        "-i", str(adjusted_audio_path),
                        "-filter_complex",
                        f"[1:a]adelay={int(pause_before * 1000)}|{int(pause_before * 1000)},apad[a]",
                        "-map", "0:v", "-map", "[a]",
                        "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "192k",
                        "-t", str(total_dur),
                        "-r", "30",
                        str(segment_path),
                    ],
                    capture_output=True,
                )
                segments.append(segment_path)

        # Concatenate all segments
        concat_file = tmpdir / "concat.txt"
        with open(concat_file, "w") as f:
            for seg in segments:
                f.write(f"file '{seg}'\n")

        print("  Combining segments...")
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                str(output_path),
            ],
            capture_output=True,
        )


def main():
    parser = argparse.ArgumentParser(description="SpeakCards - English flashcard video generator")
    parser.add_argument("input", help="Text file with one English sentence per line")
    parser.add_argument("-o", "--output", default="output.mp4", help="Output video file (default: output.mp4)")
    parser.add_argument("--pause-before", type=float, default=1.0, help="Pause before speech in seconds (default: 1.0)")
    parser.add_argument("--pause-after", type=float, default=1.5, help="Pause after speech in seconds (default: 1.5)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found")
        return

    sentences = [line.strip() for line in input_path.read_text().splitlines() if line.strip()]
    if not sentences:
        print("Error: No sentences found in input file")
        return

    print(f"SpeakCards: Generating video with {len(sentences)} cards...")
    build_video(sentences, args.output, args.pause_before, args.pause_after)
    print(f"Done! Video saved to: {args.output}")


if __name__ == "__main__":
    main()
