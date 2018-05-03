var mapContainer = document.getElementById('map-container');

var RknCoordinates = {
  lat: 55.7558,
  lng: 37.6173
};

var mapOptions = {
  zoom: 2,
  height: 600,
  width: 900
};

var defaultLayers = platform.createDefaultLayers();

var map = new H.Map(
  mapContainer,
  defaultLayers.normal.map,
  mapOptions);

var circles = []

var iconOptions = {
  size: new H.math.Size(50, 50),
  anchor: new H.math.Point(25, 25)
};

var markerOptions = {
  icon: new H.map.Icon(iconUrl, iconOptions)
};

var marker = new H.map.Marker(RknCoordinates, markerOptions);
map.addObject(marker);

var mapTileService = platform.getMapTileService({
    type: 'base'
  }),
  russianMapLayer = mapTileService.createTileLayer(
    'maptile',
    'normal.day',
    256,
    'png8',
    {lg: 'RUS'}
  );
map.setBaseLayer(russianMapLayer);


var behavior = new H.mapevents.Behavior(new H.mapevents.MapEvents(map));
var ui = H.ui.UI.createDefault(map, defaultLayers, 'ru-RU');

function prettyScaling(size, zoom) {
  threshold = 32
  base = 2 ** 10
  if (size < threshold) {
    radius = (size) / zoom;
  } else {
    radius = (threshold + Math.log(size - threshold + 1)) / zoom;
  }
  return base + radius * (2 ** 20 / threshold);
}

setInterval(function() {
  for (var i = 0; i < circles.length; ++i) {
    var lat = circles[i].geom.getCenter().lat;
    circles[i].geom.setRadius(prettyScaling(circles[i].size, 2 << map.getZoom())*Math.cos((180 / Math.PI)*lat));
  }
}, 500);


window.addEventListener('resize', function () {
  map.getViewPort().resize();
});

$('#submitform').submit(function(e){
  e.preventDefault();
  $.ajax({
    url: '/filter',
    type: 'post',
    data: $('#submitform').serialize(),
    success: function(points) {
      for (var i = 0; i < circles.length; ++i) {
        map.removeObject(circles[i].geom);
      }

      circles = []

      for (var i = 0; i < points.length; ++i) {
        var circle = new H.map.Circle(
          { lat: points[i].lat, lng: points[i].lng },
          prettyScaling(points[i].count, 2 << map.getZoom())*Math.cos((180 / Math.PI)*points[i].lat),
          {style: {fillColor: points[i].fill_color, strokeColor: 'black', lineWidth: 0}})

        circle.setData(points[i].lat.toString() + ' ' + points[i].lng.toString());

        circle.addEventListener('tap', function (evt) {
          var bubble =  new H.ui.InfoBubble(evt.target.getCenter(), {
            content: evt.target.getData()
          });
          ui.addBubble(bubble);
        }, false);

        circles.push({size: points[i].count, geom: circle});

        map.addObject(circle);
      }

      for (var i = 0; i < points.length; ++i) {
        var circle = new H.map.Circle(
          { lat: points[i].lat, lng: points[i].lng },
          prettyScaling(points[i].count, 2 << map.getZoom())*Math.cos((180 / Math.PI)*points[i].lat),
          {style: {fillColor: 'rgba(0, 0, 0, 0)', strokeColor: points[i].fill_color, lineWidth: 1.0}})

        circles.push({size: points[i].count, geom: circle});

        map.addObject(circle);
      }
    }
  });
});