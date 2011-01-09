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
    }
  },
  'mathLib': {
    'gain': {
      'width': 100,
      'height': 100,
      'rotation': 0,
      'flip': false,
      'color': [0.0, 0.0, 0.0],
      'background': [1.0, 1.0, 1.0],
      'mask': [
      { 'type': 'move', 'x': 0.999, 'y': 0.5   }, // just to show what's possible
      { 'type': 'line', 'x': 0    , 'y': 0.999 },
      { 'type': 'line', 'x': 0    , 'y': 0     }  
      // auto close
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
    }
  }
};

// Die Struktur mit der feritgen Logik
var logicJSON = {};
