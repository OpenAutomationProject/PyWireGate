/* gle.connection.js (c) 2011 by Christian Mayer [CometVisu at ChristianMayer dot de]
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
 * The element that stores all informations and methods about one connection
 */

/**
 * The connection constructor.
 * type: the block (proto)type in JSON notation
 * svg: the link to the SVG canvas
 * interactive: event handlers will be added, set to false to create picture only
 */
function Connection( JSON, svg, interactive )
{
  // setup the private "constants"
  var that = this;
  var inset  = 3; // how far should the handle stick in  
  var outset = 3; // how far should the handle stick out
  
  // setup the private variables
  var origin      = JSON.origin      || undefined;
  var paths       = JSON.paths       || [];
  var branch = 0; // the current branch to edit
  var lastFixed = 0; // the last fixed position
  
  var canvas   = svg         || $('#editor').svg('get');
  var addEvent = interactive !== undefined ? interactive : true;
  var inEdit   = false;
  var g = undefined; // link to the representation of the block in the DOM
  
  // the private functions
  
  // (re)draw itself on the canvas
  function draw()
  {
    var classList = 'connection';
    if( !g ) // no lines yet? Create it...
    {
      g = canvas.group( { 'class':classList } );
    }
    var parameter = {
      class: classList,
      stroke: colorByArray( origin.getColor() ),
      'stroke-width': 1, 
      'marker-end'  : 'url(#ArrowEnd)',
      fill:  'none'
    };
    
    var lines = $(g).find( 'polyline' );
    for( var i in paths )
    {
      if( lines[i] === undefined )
        lines[i] = canvas.polyline( g, [], parameter );
      
      lines[i].setAttribute('points', paths[i].path.join(',') );
      if( paths[i].target == undefined || origin == undefined )
        lines[i].setAttribute('stroke-dasharray', '1,3'  );
      else
        lines[i].setAttribute('stroke-dasharray', 'none' );
    }
    for( var i = lines.length-1; i > paths.length; i-- )
      lines.remove( i );
    
    // shotcut
    function connectionDrag( obj, handle )
    {
      $(handle).bind( 'mousedown', {obj:obj}, connectionDragMouseDown );
    }
    
    // delete old handles
    $(g).find('rect').remove();
    // Draw the handles
    for( var i in paths )
    {
      for( var j in paths[i].path )
      {
        var x = paths[i].path[j][0];
        var y = paths[i].path[j][1];
        var style = '';
        if( j == 0 || j == paths[i].path.length-1 ) style  = 'opacity:0;';
        if( inEdit && j == paths[i].path.length-1 ) style += 'display:none';
        connectionDrag( [g,i,j], canvas.rect( g, x-outset, y-outset, 1+inset+outset, 1+inset+outset, {class:'move',style:style} ) ); 
      }
    }
    
  }
  
  function connectionDragMouseDown( event )
  {
    console.log( 'cDMD', event );
    var classList = this.getAttribute('class').split(' ');
    console.log( 'cDMD', classList );
    console.log( 'cDMD', event.data.obj );
      
    var path = paths[ event.data.obj[1] ].path;
    var extend = event.data.obj[2] == path.length - 1
    var parameter = {
      obj    : event.data.obj,
      origx  : path[ event.data.obj[2] ][0],
      origy  : path[ event.data.obj[2] ][1],
      extend : extend,
      startx : event.pageX, 
      starty : event.pageY
    };
    
    lastFixed = path.length - 1;
    
    /*
    if( extend )
    {
      this.style.display = 'none';
    }
    */
    inEdit = true;
    
    $(document).bind( 'mousemove', parameter, editorDragMouseMove );
    $(document).bind( 'mouseup'  ,            editorDragMouseUp   );
    return false;
  }
  
  function editorDragMouseMove( event )
  {
    var ed   = event.data;
    var pos = getCoordinate(event);
    //console.log('cDMM', ed );
    if( ed.extend )
    {
      that.lastMove( pos, false );
    } else {
      var path = paths[ed.obj[1]].path;
      var i = parseInt( ed.obj[2] );
      if( path[i-1] !== undefined )
      {
        if( Math.abs( path[i-1][0] - path[i][0] ) < 1.0 )
          path[i-1][0] = pos.x;
        if( Math.abs( path[i-1][1] - path[i][1] ) < 1.0 )
          path[i-1][1] = pos.y;
      }
      if( path[i+1] !== undefined )
      {
        if( Math.abs( path[i+1][0] - path[i][0] ) < 1.0 )
          path[i+1][0] = pos.x;
        if( Math.abs( path[i+1][1] - path[i][1] ) < 1.0 )
          path[i+1][1] = pos.y;
      }
      path[i][0] = pos.x;
      path[i][1] = pos.y;
      // simplify path, i.e. delete double points
      for( var j = path.length-1; j > 0; j-- )
      {
        if( i == j || i == j-1 ) continue; // don't delete current point
        if( Math.abs( path[j-1][0] - path[j][0] ) < 1.0 &&
            Math.abs( path[j-1][1] - path[j][1] ) < 1.0 )
        {
          path.splice( j-1, 2 );
          if( j < i ) ed.obj[2] -= 2;
        }
      }
      draw();
    }
  }
  
  function editorDragMouseUp( event )
  {
    $(document).unbind( 'mousemove', editorDragMouseMove );
    $(document).unbind( 'mouseup'  , editorDragMouseUp   );
    inEdit = false;
      var target = that.lastTarget();
      if( target )
      {
        target.block.setConnection( target.type, target.number, that ); //event.data.con );
      }
    draw();
  }
  
  
  this.firstMove = function( pos )
  {
    pos = [ pos.x, pos.y ]; // convert
    if( Math.abs( paths[0].path[0][1] - paths[0].path[1][1] ) < 1.0 ) // keep horizontal line
    {
      paths[0].path[0] = pos;
      paths[0].path[1][1] = pos[1];
    } else {
      paths[0].path[0] = pos;
    }
    // remove obsolete points if the are the same now
    if( paths[0].path.length > 3                                    &&
        Math.abs( paths[0].path[1][0] - paths[0].path[2][0] ) < 1.0 &&
        Math.abs( paths[0].path[1][1] - paths[0].path[2][1] ) < 1.0 )
    {
      console.log( 'firstMove', paths[0].path.length );
      lastFixed -= 2;
      paths[0].path.shift(); // remove front
      paths[0].path.shift(); // remove first identical
      paths[0].path[0] = pos; // remove second identical by setting it to the first
    }
    draw();
  }
  
  this.lastMove = function( pos, force )
  {
    if( lastFixed < 0 ) lastFixed = 0; // sanity check...
    while( paths[branch].path.length > lastFixed+1 )
      paths[branch].path.pop();
    var start = paths[branch].path[ paths[branch].path.length - 1 ];
    var op = overPort;
    if( !force && op && op.type == 'inPort' )
    {
      pos = op.block.inPortPos( op.number )[0];
    }
    if( force || (op && op.type == 'inPort') )
    {
      paths[branch].target = op;
      if( Math.abs( start[1] - pos.y ) > 1.0 )
        paths[branch].path.push( [ (pos.x+start[0])/2, start[1] ] );
      paths[branch].path.push( [ (pos.x+start[0])/2, pos.y ] );
    } else {
      paths[branch].target = undefined;
      if( Math.abs( start[1] - pos.y ) > 1.0 )
        paths[branch].path.push( [ pos.x, start[1] ] );
    }
    paths[branch].path.push( [pos.x, pos.y] );
    draw();
  }
  
  this.lastTarget = function()
  {
    return paths[branch].target;
  }
  
  // Dump this Block in JSON notation to serialize it
  this.getJSON = function()
  {
    return {
      origin      : origin,
      paths       : paths
    };
  }
}

