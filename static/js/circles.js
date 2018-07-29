var mapContainer = document.getElementById('map-container');

var RknCoordinates = {
  lat: 55.75155,
  lng: 37.6365
};

var mapOptions = {
  zoom: 2,
  height: 600,
  width: 900,
  noWrap: true
};

// var defaultLayers = platform.createDefaultLayers();

var map = L.map('map-container').setView([20, 0], 2);

L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw', {
  maxZoom: 18,
  attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors, ' +
    '<a href="https://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, ' +
    'Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
  id: 'mapbox.streets'
}).addTo(map);

// var map = new H.Map(
//   mapContainer,
//   defaultLayers.normal.map,
//   mapOptions);

var circles = []

// var iconOptions = {
//   size: new H.math.Size(81, 50),
//   anchor: new H.math.Point(25, 25)
// };

// var markerOptions = {
//   icon: new H.map.Icon(iconUrl, iconOptions)
// };

// var marker = new H.map.Marker(RknCoordinates, markerOptions);
// map.addObject(marker);

// var mapTileService = platform.getMapTileService({
//     type: 'base'
//   }),
//   russianMapLayer = mapTileService.createTileLayer(
//     'maptile',
//     'normal.day',
//     256,
//     'png8',
//     {lg: 'RUS'}
//   );
// map.setBaseLayer(russianMapLayer);


// var behavior = new H.mapevents.Behavior(new H.mapevents.MapEvents(map));
// var ui = H.ui.UI.createDefault(map, defaultLayers, 'ru-RU');

function prettyScaling(size, zoom) {
  threshold = 32
  base = 2 ** 10.5
  if (size < threshold) {
    radius = (size) / zoom;
  } else {
    radius = (threshold + Math.pow(size - threshold + 1, 0.25)) / zoom;
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
  map.invalidateSize();
});

Highcharts.Axis.prototype.log2lin = function (num) {
    return Math.log(num) / Math.LN2;
};

Highcharts.Axis.prototype.lin2log = function (num) {
    return Math.pow(2, num);
};
    

$('#submitform').submit(function(e){
  e.preventDefault();
  $.ajax({
    url: '/filter',
    type: 'post',
    data: $('#submitform').serialize(),
    success: function(data) {
      for (var i = 0; i < circles.length; ++i) {
        map.removeLayer(circles[i].geom);
      }

      var points = data['gps'];
      circles = [];

      console.log(points);

      for (var i = 0; i < points.length; ++i) {
        var circle = new L.Circle(
          [points[i].lat, points[i].lng],
          {radius: prettyScaling(points[i].count, 2 << map.getZoom())*Math.cos((180 / Math.PI)*points[i].lat),
          color: 'black', fillColor: points[i].fill_color, 
          fillOpacity: '0.7', weight: 0})

        circle.bindPopup(points[i].lat.toString() + ' ' + points[i].lng.toString());
        // circle.setData(points[i].lat.toString() + ' ' + points[i].lng.toString());

        // circle.addEventListener('tap', function (evt) {
        //   var bubble =  new H.ui.InfoBubble(evt.target.getCenter(), {
        //     content: evt.target.getData()
        //   });
        //   ui.addBubble(bubble);
        // }, false);

        circles.push({size: points[i].count, geom: circle});

        circle.addTo(map);
      }

      // for (var i = 0; i < points.length; ++i) {
      //   var circle = new L.Circle(
      //     [points[i].lat, points[i].lng],
      //     {radius: prettyScaling(points[i].count, 2 << map.getZoom())*Math.cos((180 / Math.PI)*points[i].lat),
      //     color: 'black', weight: 2.0})
        
      //   circles.push({size: points[i].count, geom: circle});

      //   circle.addTo(map);
      // }

      // for (var i = 0; i < points.length; ++i) {
      //   var circle = new L.Circle(
      //     [points[i].lat, points[i].lng],
      //     {radius: prettyScaling(points[i].count, 2 << map.getZoom())*Math.cos((180 / Math.PI)*points[i].lat),
      //     color: points[i].fill_color, weight: 1.0})

      //   circles.push({size: points[i].count, geom: circle});

      //   circle.addTo(map);
      // }

      var stats = data['stats'];
        Highcharts.chart('chart-container', {
        chart: {
            height: 400,
            type: 'column'
        },
        title: {
            text: 'График блокировок по дням'
        },
        xAxis: {        
            type: 'datetime',
            ordinal: false,
            labels: {
                formatter: function() {
                    return Highcharts.dateFormat('%d.%m.%Y', this.value);
                }
            }
        },
        yAxis: {
            type: 'logarithmic',
            title: {
                text: 'Количество адресов'
            },
            min: 0.3125,
            max: 2 << 22,
            startOnTick: false,
            labels: {
                formatter: function() {
                    console.log(this.value);
                    if (this.value < 1) {
                        return 0;
                    } else {
                        return Highcharts.Axis.prototype.defaultLabelFormatter.call(this);
                    }
                },
            }, 

        },
        legend: {
            layout: 'vertical',
            align: 'left',
            floating: true,
            x: 100,
            y: 50,
            verticalAlign: 'top',
            labelFormatter: function() {
                var total = 0;
                for (var i=this.yData.length; i--;) { total += this.yData[i]; };
                    return this.name + ': ' + total + ' адресов';
            }
        },

        plotOptions: {
            series: {
                label: {
                    connectorAllowed: false
                },
            }
        },

        series: stats,

        responsive: {
            rules: [{
                condition: {
                    maxWidth: 500
                },
                chartOptions: {
                    legend: {
                        layout: 'horizontal',
                        align: 'center',
                        verticalAlign: 'bottom'
                    }
                }
            }]
        }
      });     
    }
  });
});
