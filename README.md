# SpeakCards

英語学習用のフラッシュカード動画を自動生成するツール。
英文テキストファイルを入力するだけで、TTS音声付きのスライド動画を作成します。

## Requirements

- Python 3.9+
- FFmpeg

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
# 基本的な使い方
python speakcards.py sentences.txt

# 出力ファイル名を指定
python speakcards.py sentences.txt -o my_video.mp4

# 音声前後のポーズを調整
python speakcards.py sentences.txt --pause-before 2.0 --pause-after 2.0
```

## Input Format

1行1文の英文テキストファイル:

```
I have a pen.
This is an apple.
She goes to school every day.
```
