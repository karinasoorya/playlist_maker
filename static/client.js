$(document).ready(function () {
    $("img.image_selector").click(function () {
      var id = this.id;
      $.get('/put_param/' + id, function(thing) {
          window.location.href = "http://localhost:8000/audio_features/" + id;
      });
    });
});
