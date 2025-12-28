# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, jsonify
import os
from openai import OpenAI
from io import BytesIO

app = Flask(__name__)

# OpenAI APIキーの設定
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    """
    音声をWhisper APIで文字起こしする
    スピーカー識別機能付き（gpt-4o-transcribe-diarize）
    """
    try:
        # リクエストからオーディオデータを取得
        if 'audio' not in request.files:
            return jsonify({'error': 'オーディオファイルが送信されていません'}), 400
        
        audio_file = request.files['audio']
        
        if audio_file.filename == '':
            return jsonify({'error': 'ファイルが選択されていません'}), 400
        
        # バイナリデータを読み込む
        audio_data = audio_file.read()
        
        # 空のデータの場合はスキップ
        if len(audio_data) == 0:
            return jsonify({
                'success': True,
                'text': '',
                'segments': []
            })
        
        # BytesIOでラップしてOpenAI APIに送信
        audio_stream = BytesIO(audio_data)
        audio_stream.name = 'audio.webm'
        
        try:
            # gpt-4o-transcribe-diarizeでスピーカー識別
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-transcribe-diarize",
                file=audio_stream,
                response_format="diarized_json",
                chunking_strategy="auto"
            )
            
            # フルテキストを取得
            full_text = getattr(transcript, 'text', '')
            
            # AIで文章を整える
            if full_text:
                full_text = refine_text(full_text)
            
            # セグメント情報を抽出
            segments = []
            if hasattr(transcript, 'segments') and transcript.segments:
                for segment in transcript.segments:
                    segments.append({
                        'speaker': getattr(segment, 'speaker', f'Speaker {len(segments) % 3 + 1}'),
                        'text': getattr(segment, 'text', ''),
                        'start': getattr(segment, 'start', 0),
                        'end': getattr(segment, 'end', 0)
                    })
            
            return jsonify({
                'success': True,
                'text': full_text,
                'segments': segments
            })
        
        except Exception as diarize_error:
            # diarizeが失敗した場合、gpt-4o-mini-transcribeにフォールバック
            print(f"Diarize error: {diarize_error}")
            audio_stream.seek(0)
            
            try:
                transcript = client.audio.transcriptions.create(
                    model="gpt-4o-mini-transcribe",
                    file=audio_stream
                )
                
                text = getattr(transcript, 'text', '')
                if text:
                    text = refine_text(text)
                
                segments = [{
                    'speaker': 'Speaker',
                    'text': text,
                    'start': 0,
                    'end': 0
                }]
                
                return jsonify({
                    'success': True,
                    'text': text,
                    'segments': segments
                })
            except Exception as mini_error:
                # 最後のフォールバック：whisper-1
                print(f"Mini error: {mini_error}")
                audio_stream.seek(0)
                
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_stream,
                    language="ja"
                )
                
                text = getattr(transcript, 'text', '')
                if text:
                    text = refine_text(text)
                
                segments = [{
                    'speaker': 'Speaker',
                    'text': text,
                    'start': 0,
                    'end': 0
                }]
                
                return jsonify({
                    'success': True,
                    'text': text,
                    'segments': segments
                })
    
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Error: {error_msg}")
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

def refine_text(text):
    """
    AIで日本語の文章を自然な形に整える
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "あなたは日本語の文章を自然で読みやすい形に整えるアシスタントです。"
                },
                {
                    "role": "user",
                    "content": f"""以下の音声認識結果を、自然で読みやすい日本語に整えてください。

要件：
- 「えっと」「あの」「で、」などの口癖を削除する
- 句読点を適切に追加する
- カタカナを適切な漢字に変換する（例：ナンバー→難波、キンシチョー→金四町）
- 固有名詞（地名、人名など）は正しい表記に修正する
- 意味は変えずに、自然な日本語にする
- 元の意図は損なわないようにする

音声認識結果：
{text}

整えた文章だけを出力してください。"""
                }
            ]
        )
        
        refined = response.choices[0].message.content.strip()
        return refined
    except Exception as e:
        print(f"Text refinement error: {e}")
        # エラーの場合は元のテキストをそのまま返す
        return text

if __name__ == '__main__':
    app.run(debug=True, port=5000)

