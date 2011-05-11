 // Sollte das Backend dynamisch aus den verfuegbaren Bloecken generieren:
 /*var libJSON = {
  'sourceLib': {
    'source1': {
      'width': 100,
      'height': 50,
      'rotation': 0,
      'flip': false,
      'color': [0.0, 0.0, 0.0],
      'background': [1.0, 1.0, 1.0],
      'inPorts': [],
      'outPorts': [
        { 
          'name': 'out1',
          'type': 'event'
        }
      ],
      'parameters':{}
    },
    'source2': {
      'width': 100,
      'height': 100,
      'rotation': 0,
      'flip': false,
      'color': [0.0, 0.0, 1.0],
      'background': [1.0, 1.0, 0.5],
      'inPorts': [],
      'outPorts': [
        { 
          'name': 'out1',
          'type': 'event'
        },
        { 
          'name': 'out2',
          'type': 'event'
        }
      ],
      'parameters':{}
    }
  },
  'sinkLib': {
    'sink1': {
      'width': 100,
      'height': 100,
      'rotation': 0,
      'flip': false,
      'color': [0.0, 0.0, 0.0],
      'background': [1.0, 1.0, 1.0],
      'inPorts': [
        { 
          'name': 'in',
          'type': 'event'
        }
      ],
      'outPorts': [],
      'parameters':{}
    },
    'sink2': {
      'width': 100,
      'height': 100,
      'rotation': 0,
      'flip': false,
      'color': [0.0, 0.0, 0.0],
      'background': [1.0, 1.0, 1.0],
      'inPorts': [
      { 
        'name': 'in',
        'type': 'event'
      },
      { 
        'name': 'in',
        'type': 'event'
      },
      { 
        'name': 'in',
        'type': 'event'
      },
      { 
        'name': 'in',
        'type': 'event'
      }
      ],
      'outPorts': [],
      'parameters':{}
    }
  },
  'mathLib': {
    'gain': {
      'width': 75,
      'height': 75,
      'rotation': 0,
      'flip': false,
      'color': [0.0, 0.0, 0.0],
      'background': [1.0, 1.0, 1.0],
      'mask': [
      { 'type': 'move', 'x': 0.999, 'y': 0.5   }, // it must allways start with a move!
      { 'type': 'line', 'x': 0    , 'y': 0.999 },
      { 'type': 'line', 'x': 0    , 'y': 0     },
      { 'type': 'close' },
      { 'type': 'new', 'fill': 'none' },
      { 'type': 'text', 'x': 0.4, 'y': 0.55, 'text': '$gain', 'styling':['middle'] }
      ],
      'maskOptions': {
        'showLabel': false
      },
      'inPorts': [
        { 
          'name': 'in',
          'type': 'event'
        }
      ],
      'outPorts': [
        { 
          'name': 'out',
          'type': 'event'
        }
      ],
      'parameters': [
        { 
          'name': 'gain',
          'type': 'float',
          'default': 1.0
        }
      ]
    },
    'sum': {
      'width': 50,
      'height': 50,
      'rotation': 0,
      'flip': false,
      'color': [0.0, 0.0, 0.0],
      'background': [1.0, 1.0, 1.0],
      'mask': [
      { 'type': 'move', 'x': 0    , 'y': 0.495  }, 
      { 'type': 'arc' , 'x': 0    , 'y': 0.01   , 
        'rx': 0.5, 'ry': 0.5, 'xRotate':0, 'large':true, 'clockwise': true,
        'relative': true
      },
      { 'type': 'close' }
      ],
      'maskOptions': {
        'showLabel': true,
        'inPortPos': function( nr, block, options, parameter ){
          var x = block.getX();
          var y = block.getY();
          var width  = block.getWidth();
          var height = block.getHeight();
          var type = parameter.inputs.split('');
          if( type.length < 1 )
            return [ 
              { x: x   , y: y + height / 2 },
              { x: x-10, y: y + height / 2 }
            ];
          for( var i = 0; i < type.length; i++ )
          {
            if( type[i] != '|' )
            {
              if( nr == 0 )
              {
                var angle = Math.PI * (0.5 + i / (type.length-1));
                var s = Math.sin( angle );
                var c = Math.cos( angle );
                return [ { x: x + width  * 0.5 * ( 1 + c ),
                           y: y + height * 0.5 * ( 1 - s ) },
                         { x: x + width  * 0.5 + (width +40) * 0.5 * c,
                           y: y + height * 0.5 - (height+40) * 0.5 * s }
                       ];
              }
              nr--;
            }
          }
          return [ {x: undefined, y: undefined}, {x: undefined, y: undefined} ];
        },
        'postParameterUpdate': function( context, parameter ){
          var inPorts = [];
          for( i in parameter.inputs )
          {
            switch( parameter.inputs[i] )
            {
              case '+':
                inPorts.push( { name: '+', type: 'event' } );
                break;
              case '-':
                inPorts.push( { name: '-', type: 'event' } );
                break;
              default: // e.g. '|'
                break;
            }
          }
          return { inPorts: inPorts };
        }
      },
      'inPorts': [
      { 
        'name': '+',
        'type': 'event'
      },
      { 
        'name': '+',
        'type': 'event'
      }
      ],
      'outPorts': [
      { 
        'name': 'out',
        'type': 'event'
      }
      ],
      'parameters': [
      { 
        'name': 'inputs',
        'type': 'string',
        'default': '|++'
      }
      ]
    },
    'integral': {
      'width': 75,
      'height': 75,
      'rotation': 0,
      'flip': false,
      'color': [0.0, 0.0, 0.0],
      'background': [1.0, 1.0, 1.0],
      'mask': [
      { 'type': 'move', 'x': 0    , 'y': 0     }, // it must allways start with a move!
      { 'type': 'line', 'x': 0    , 'y': 0.999 },
      { 'type': 'line', 'x': 0.999, 'y': 0.999 },
      { 'type': 'line', 'x': 0.999, 'y': 0     },
      { 'type': 'close' },
      { 'type': 'new', 'fill': 'none' },
      { 'type': 'move', 'x': 0.55 , 'y': 0.1   }, 
      { 'type': 'arc' , 'x': 0.50  , 'y': 0.1    , 
        'rx': 0.025, 'ry': 0.025, 'xRotate':0, 'large':true, 'clockwise': false,
        'relative': false
      },
      { 'type': 'line', 'x': 0.5  , 'y': 0.9   },
      { 'type': 'arc' , 'x': 0.45 , 'y': 0.9    , 
        'rx': 0.025, 'ry': 0.025, 'xRotate':0, 'large':true, 'clockwise': true,
        'relative': false
      },
      { 'type': 'text', 'x': 0.6, 'y': 0.5, 'text': 'd' },
      { 'type': 'text', 'x': 0.6, 'y': 0.5, 'text': '\u2002t', 'styling':['italic'] }
      ],
      'maskOptions': {
        'showLabel': false
      },
      'inPorts': [
      { 
        'name': 'in',
        'type': 'event'
      }
      ],
      'outPorts': [
      { 
        'name': 'out',
        'type': 'event'
      }
      ],
      'parameters': [
      ]
    }
  }
};*/

var libJSON = {};
$.getJSON('/logicLib', function(data) {
  libJSON = data;
  drawLibrary();
});

// The array with all known logics (should be filled on demand later)
var logics = {};
$.getJSON('/logicCode/logik.json', function(data) {
  logics['logik'] = data;
  updateKnownLogics('logik');
});
$.getJSON('/logicCode/logik2.json', function(data) {
  logics['logik2'] = data;
  updateKnownLogics('logik2');
});

// tweak backend communication, should also be done on demand
live = new CometVisu( '/live/' );
liveUpdateCalls = [];
count = 10;
live.update = function( json )
{
  $.each( liveUpdateCalls, function(){
    for( var i = 0; i < json.length; i++ )
    {
      var last = i == json.length-1;
      if( json[i].block == this[0] && ( last || !this[1] ) )
      {
        this[2]( json[i].value );
      }
    }
  });
}
live.subscribe( ['ALL'] );

$(window).unload(function() {
  live.stop();
});