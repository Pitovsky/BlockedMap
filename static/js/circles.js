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


map.setBaseLayer(defaultLayers.terrain.map);
var behavior = new H.mapevents.Behavior(new H.mapevents.MapEvents(map));
var ui = H.ui.UI.createDefault(map, defaultLayers);

setInterval(function() {
  for (var i = 0; i < circles.length; ++i) {
    var lat = circles[i].geom.getCenter().lat;
    circles[i].geom.setRadius((256000*Math.log(circles[i].size)*Math.cos((180 / Math.PI)*lat) + 500) / (2 << map.getZoom()));
  }
}, 500);


window.addEventListener('resize', function () {
  map.getViewPort().resize();
});

$('#submitform').submit(function(e){
  e.preventDefault();
  $.ajax({
    url:'/filter',
    type:'post',
    data:$('#submitform').serialize(),
    success:function(points){
      for (var i = 0; i < circles.length; ++i) {
        map.removeObject(circles[i].geom);
      }
      circles = [];
      for (var i = 0; i < points.length; ++i) {
        circles.push({size: points[i].count, geom: new H.map.Circle(
          { lat: points[i].lat, lng: points[i].lng },
          (256000*Math.log(points[i].count)*Math.cos((180 / Math.PI)*points[i].lat) + 500) / (2 << map.getZoom()),
          {style: {fillColor: points[i].color, strokeColor: 'black', lineWidth: 0.3}})
        });
        map.addObject(circles[i].geom);
      }
    }
  });
});