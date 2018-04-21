var mapContainer = document.getElementById('map-container');

var platform = new H.service.Platform({
  app_id: '{id}',
  app_code: '{code}',
});

var MoscowCoordinates = {
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

window.addEventListener('resize', function () {
  map.getViewPort().resize();
});

var behavior = new H.mapevents.Behavior(new H.mapevents.MapEvents(map));
var ui = H.ui.UI.createDefault(map, defaultLayers);

var marker = new H.map.Marker(MoscowCoordinates);
map.addObject(marker);