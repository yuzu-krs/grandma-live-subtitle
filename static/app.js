let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let stream = null;

const recordBtn = document.getElementById("recordBtn");
const transcriptDiv = document.getElementById("transcript");
const statusDiv = document.getElementById("status");

// ボタンイベント（長押し：開始、離す：停止）
recordBtn.addEventListener("mousedown", startRecording);
recordBtn.addEventListener("mouseup", stopRecording);
recordBtn.addEventListener("mouseleave", stopRecording);
recordBtn.addEventListener("touchstart", startRecording);
recordBtn.addEventListener("touchend", stopRecording);

// 録音開始（ボタン押下）
async function startRecording(e) {
  e.preventDefault();
  if (isRecording) return;

  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    isRecording = true;
    audioChunks = [];

    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (event) => {
      audioChunks.push(event.data);
    };
    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
      await transcribeAudio(audioBlob);
    };

    mediaRecorder.start();
    recordBtn.textContent = "🔴 聞き取り中...";
    statusDiv.textContent = "";
  } catch (error) {
    console.error("マイクエラー:", error);
    alert("マイクを許可してください");
    statusDiv.textContent = "マイクが使えません";
  }
}

// 録音停止（ボタン離す）
function stopRecording(e) {
  e.preventDefault();
  if (!mediaRecorder || !isRecording) return;

  mediaRecorder.stop();
  isRecording = false;
  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
  }
  recordBtn.textContent = "🎙️ 押して話す";
  statusDiv.textContent = "文字起こし中...";
}

// 音声を文字起こし
async function transcribeAudio(audioBlob) {
  try {
    const formData = new FormData();
    formData.append("audio", audioBlob, "audio.webm");

    const response = await fetch("/transcribe", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error("サーバーエラー: " + response.status);
    }

    const result = await response.json();

    if (result.success) {
      // テキストのみ表示（話者情報は表示しない）
      if (result.text) {
        transcriptDiv.textContent = result.text;
      }
      statusDiv.textContent = "完了 ✓";
    } else {
      statusDiv.textContent = "エラーが発生しました";
    }
  } catch (error) {
    console.error("エラー:", error);
    statusDiv.textContent = "エラー: " + error.message;
  }
}
