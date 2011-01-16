/* gle.block.js (c) 2011 by Christian Mayer [CometVisu at ChristianMayer dot de]
 * 
 * This program is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the Free
 * Software Foundation; either version 3 of the License, or (at your option)
 * any later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
 * more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA
 */

/**
 * The element that stores all informations and methods about one block
 */

/**
 * The block constructor.
 * type: the block (proto)type in JSON notation
 * svg: the link to the SVG canvas
 * interactive: event handlers will be added, set to false to create picture only
 */
function Block( type, svg, interactive )
{
  // setup the private "constants"
  var that = this;
  var inset  = 3; // how far should the handle stick in  
  var outset = 3; // how far should the handle stick out
  
  // setup the private variables
  var x           = type.x           || 0;
  var y           = type.y           || 0;
  var width       = type.width       || 100;
  var height      = type.height      || 100;
  var rotation    = type.rotation    || 0;
  var flip        = type.flip        || false;
  var mask        = type.mask        || undefined;
  var maskOptions = type.maskOptions || { showLabel: true };
  var color       = type.color       || [0.0, 0.0, 0.0];
  var background  = type.background  || [1.0, 1.0, 1.0];
  var inPorts     = type.inPorts     || [];
  var outPorts    = type.outPorts    || [];
  var parameters  = type.parameters  || {};
  
  var canvas   = svg         || $('#editor').svg('get');
  var addEvent = interactive !== undefined ? interactive : true;
  var g = undefined; // link to the representation of the block in the DOM
  
  // the private functions
  
  // (re)draw itself on the canvas
  function draw()
  {
    var classList = 'block';
    if( g ) 
    {
      classList = g.getAttribute('class');
      g.parentNode.removeChild( g ); // delete the old representation
    }
    g = canvas.group( {'transform':'translate(' + x + ',' + y + ')', 'class':classList} );

    // helper function to scale relative positioning
    function scaleRelPos( value, absValue )
    {
      if( value >= 1.0 ) return value; // it is already absolutely scaled
      if( value <  0   ) return absValue + value; // absolutely from right
      return absValue * value; // relative scaled
    }
    
    var style = {
      fill:   colorByArray( background ), 
      stroke: colorByArray( color      ),
      'stroke-width': 1 
    };
    
    // Draw the body
    var body = canvas.group( g, {'transform':'translate(6,1)'} );
    if( mask )
    {
      var path = canvas.createPath();
      for( var i in mask )
      {
        var obj = mask[i];
        var sx = scaleRelPos( obj.x, width  ); 
        var sy = scaleRelPos( obj.y, height ); 
        switch( obj.type )
        {
          case 'move':
            path.move( sx, sy );
            break;
            
          case 'line':
            path.line( sx, sy );
            break;
        }
      }
      canvas.path( body, path.close(), style );
    } else {
      canvas.rect( body, 0, 0, width, height, style );
    }
    if( addEvent ) editorConnectionPointCreate( body, undefined, undefined );
    
    // extend the style for the ports...
    style.cursor = 'crosshair';
    style.fill = style.stroke;
    
    // Draw the inports
    var inPortsLength  = inPorts.length;
    $.each( inPorts, function(i){
      var y = 1 + height * (0.5 + i)/inPortsLength;
      if( 'connection' in this )
        canvas.line( g, 0, y, 6, y, style );
      else
        editorConnectionPointCreate( canvas.polyline( g, [[1, y-4],[6, y],[1, y+4]], style ), 'inPort', i );
      if( maskOptions.showLabel )
        canvas.text( g, 10, y, this.name, {'dominant-baseline':'middle','text-anchor':'start'} );
    });
    
    // Draw the outports
    var outPortsLength = outPorts.length;
    $.each( outPorts, function(i){
      var y = 1 + height * (0.5 + i)/outPortsLength;
      if( 'connection' in this )
        canvas.line( g, width+6, y, width+12, y, style );
      else
        editorConnectionPointCreate( canvas.polyline( g, [[width+6, y-4],[width+11, y],[width+6, y+4]], style ), 'outPort', i );
      if( maskOptions.showLabel )
        canvas.text( g, width, y, this.name, {'dominant-baseline':'middle','text-anchor':'end'} );
    });
    
    // shotcut
    function editorDrag( obj, handle )
    {
      if( addEvent )
      {
        $(handle).bind( 'mousedown', {obj:obj}, editorDragMouseDown );
      }
    }
    
    editorDrag( g, g ); // move
    // Draw the handles
    editorDrag( g, canvas.rect( g, 5-outset     , -outset       , 1+inset+outset, 1+inset+outset, {class:'nw-resize'} ) ); 
    editorDrag( g, canvas.rect( g, 6+width-inset, -outset       , 1+inset+outset, 1+inset+outset, {class:'ne-resize'} ) );
    editorDrag( g, canvas.rect( g, 5-outset     , height+1-inset, 1+inset+outset, 1+inset+outset, {class:'sw-resize'} ) );
    editorDrag( g, canvas.rect( g, 6+width-inset, height+1-inset, 1+inset+outset, 1+inset+outset, {class:'se-resize'} ) );
    
  }
  
  // relocate itself on the canvas
  function relocate()
  {
    if( !g ) return draw();  // nothing to relocate...
    g.setAttribute( 'transform', 'translate(' + x + ',' + y + ')' );
  }
  
  function editorDragMouseDown( event )
  {
    console.log( 'eDMD', event );
    var classList = this.getAttribute('class').split(' ');
    console.log( 'eDMD', classList );
    var type = 'move';
    for( var i = 0; i < classList.length; i++ )
      if( classList[i] != '' && classList[i] != 'selected' && classList[i] != 'block' ) type = classList[i];
    if( $.inArray('selected', classList) == -1 && type=='move' ) editorSelect( this );
      
    var parameter = {
      type   : type,
      origx  : x, 
      origy  : y,
      origw  : width, 
      origh  : height,
      startx : event.pageX, 
      starty : event.pageY
    };
    
    $(document).bind( 'mousemove', parameter, editorDragMouseMove );
    $(document).bind( 'mouseup'  ,            editorDragMouseUp   );
    return false;
  }
  
  function editorDragMouseMove( event )
  {
    var ed   = event.data;
    switch( event.data.type )
    {
      case 'move':
        x      = ed.origx - ed.startx + event.pageX;
        y      = ed.origy - ed.starty + event.pageY;
        break;
      case 'nw-resize':
        x      = ed.origx - ed.startx + event.pageX;
        width  = ed.origw + ed.startx - event.pageX;
        y      = ed.origy - ed.starty + event.pageY;
        height = ed.origh + ed.starty - event.pageY;
        break;
      case 'ne-resize':
        width  = ed.origw - ed.startx + event.pageX;
        y      = ed.origy - ed.starty + event.pageY;
        height = ed.origh + ed.starty - event.pageY;
        break;
      case 'se-resize':
        height = ed.origh - ed.starty + event.pageY;
        width  = ed.origw - ed.startx + event.pageX;
        break;
      case 'sw-resize':
        height = ed.origh - ed.starty + event.pageY;
        x      = ed.origx - ed.startx + event.pageX;
        width  = ed.origw + ed.startx - event.pageX;
        break;
    }
    if( 'move' == event.data.type )
    {
      relocate(); // shortcut
    } else {
      if( width  < 10 ) width  = 10; // sanity...
      if( height < 10 ) height = 10; // sanity...
      draw();
    }
    
    $.each( inPorts, function(i){
      //if( 'connection' in this )
      if( this.connection !== undefined )
      {
        this.connection.lastMove( that.inPortPos( i ), true );
      }
    });
    
    $.each( outPorts, function(i){
      if( 'connection' in this )
      {
        this.connection.firstMove( that.outPortPos( i ) );
      }
    });
  }
  
  function editorDragMouseUp( event )
  {
    $(document).unbind( 'mousemove', editorDragMouseMove );
    $(document).unbind( 'mouseup'  , editorDragMouseUp   );
  }
  
  // the public (privileged) methods:
  this.getWidth  = function()          { return width ;            }
  this.setWidth  = function( _width  ) { width = _width  ; draw(); }
  this.getHeight = function()          { return height;            }
  this.setHeight = function( _height ) { height = _height; draw(); }
  this.getX      = function()          { return x     ;            }
  this.setX      = function( _x      ) { x = _x          ; draw(); }
  this.getY      = function()          { return y     ;            }
  this.setY      = function( _y      ) { y = _y          ; draw(); }
  this.getColor  = function()          { return color ;            }
  this.setColor  = function( _color  ) { color = _color  ; draw(); }
  this.setConnection = function( portType, portNumber, connection )
  {
    if( 'inPort' == portType )
      inPorts [ portNumber ].connection = connection;
    else
      outPorts[ portNumber ].connection = connection;
    draw();
  }
  this.inPortPos = function( number )
  {
    return [ x             , y + 1 + height * (0.5 + number) / inPorts.length  ];
  }
  this.outPortPos = function( number )
  {
    return [ x + width + 10, y + 1 + height * (0.5 + number) / outPorts.length ];
  }
  
  // Dump this Block in JSON notation to serialize it
  this.getJSON = function()
  {
    return {
      x           : x           ,
      y           : y           ,
      width       : width       ,
      height      : height      ,
      rotation    : rotation    ,
      flip        : flip        ,
      mask        : mask        ,
      maskOptions : maskOptions ,
      color       : color       ,
      background  : background  ,
      inPorts     : inPorts     ,
      outPorts    : outPorts    ,
      parameters  : parameters  
    };
  }
  
  // finally draw itself:
  draw();
  
  ////////////////
  function editorConnectionPointCreate( obj, portType, portNumber )
  {
    if( portType !== undefined && portNumber !== undefined )
    {
      $(obj).bind( 'mousedown', {
        portType  :portType,
        portNumber:portNumber
      }, editorConnectionPointDrag );
    }
    $(obj).bind( 'mouseover', {
      portType  :portType,
      portNumber:portNumber
    }, editorConnectionPointOverPort );
    $(obj).bind( 'mouseout', {
    }, editorConnectionPointOverPortOut );
  }
  
  function editorConnectionPointDrag( event )
  {
    console.log( 'Block: eCPD', event );
    var pn = event.data.portNumber;
    var pt = event.data.portType;
    var c = new Connection({
      origin          : that,
      originPortNumber: pn,
      paths           : [{path:[that.outPortPos( pn )]}]
    });
    that.setConnection( pt, pn,c );
    ///???
    var parameter = {con:c};
    
    $(document).bind( 'mousemove', parameter, editorConnectionPointMouseMove );
    $(document).bind( 'mouseup'  , parameter, editorConnectionPointMouseUp   );
    
    return false;
  }
  
  function editorConnectionPointMouseMove( event )
  {
    var c = getCoordinate( event );
    event.data.con.lastMove( [c.x, c.y] );
  }
  
  function editorConnectionPointMouseUp( event )
  {
    console.log( 'eCPMU' );
    $(document).unbind( 'mousemove', editorConnectionPointMouseMove );
    $(document).unbind( 'mouseup'  , editorConnectionPointMouseUp   );
    var target = event.data.con.lastTarget();
    if( target )
    {
      target.block.setConnection( target.type, target.number, event.data.con );
    }
  }
  
  function editorConnectionPointOverPort( event )
  {
    console.log( 'eCPOP', event.data.portType );
    if( event.data.portType !== undefined && event.data.portNumber !== undefined )
    {
      overPort = { 
        block : that,
        type  : event.data.portType,
        number: event.data.portNumber
      };
    } else {
      var c = getCoordinate( event );
      var distance = function( pos )
      {
        return (c.x-pos[0])*(c.x-pos[0]) + (c.y-pos[1])*(c.y-pos[1]);
      }
      if( connectionLookingForInPort )
      {
        var smallestDistance = 1e99;
        var smallestDistancePort = -1;
        for( var i = 0; i < inPorts.length; i++ )
        {
          var dist = distance( that.inPortPos(i) );
          if( dist < smallestDistance )
          {
            smallestDistance = dist;
            smallestDistancePort = i;
          }
        }
        overPort = { 
          block : that,
          type  : 'inPort',
          number: smallestDistancePort
        };
      } else {
        // FIXME ADD outPort
      }
    }
  }
  
  function editorConnectionPointOverPortOut( event )
  {
    console.log( 'eCPOPO' );
    overPort = false;
  }
}
Block.prototype = {
  globalTestFunc: function(){ alert('test'+ this.getWidth()); }
};

