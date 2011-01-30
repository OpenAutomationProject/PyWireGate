 // Sollte das Backend dynamisch aus den verfuegbaren Bloecken generieren:
 var libJSON = {
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
      { 'type': 'move', 'x': 0.999, 'y': 0.5   }, // just to show what's possible
      { 'type': 'line', 'x': 0    , 'y': 0.999 },
      { 'type': 'line', 'x': 0    , 'y': 0     },
      { 'type': 'close' }
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
          'type': 'float'
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
                         { x: x + width  * 0.5 + (width +5) * 0.5 * c,
                           y: y + height * 0.5 - (height+5) * 0.5 * s }
                       ];
              }
              nr--;
            }
          }
          return [ {x: undefined, y: undefined}, {x: undefined, y: undefined} ];
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
    }
  }
};

// Die Struktur mit der feritgen Logik
var logicJSON = {};
