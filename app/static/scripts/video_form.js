
function postVideo() {
    var videoUrl = document.getElementById('video_url').value;

    fetch('/post_video', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ video_url: videoUrl })
    })
    .then(response => {
      if (response.ok) {
        document.getElementById('video-form').style.display = 'none';
        document.getElementById('video-form-message').style.display = 'block';
      }
    });
  }
