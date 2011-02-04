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
  var origin           = JSON.origin;
  var originPortNumber = JSON.originPortNumber;
  var paths       = JSON.paths       || [];
  JSON = 0;    // not needed anymore - get it out of the closure
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
      if( lines[i*2] === undefined )
      {
        lines[i*2  ] = canvas.polyline( g, [], {fill:'none',style:'opacity:0;stroke:#fff;stroke-width:5px'} );
        $( lines[i*2] ).click( function(){editorSelect(g);} );
        lines[i*2+1] = canvas.polyline( g, [], parameter );
      }
      
      lines[i*2  ].setAttribute('points', paths[i].path.join(',') );
      lines[i*2+1].setAttribute('points', paths[i].path.join(',') );
      if( paths[i].target == undefined || origin == undefined )
        lines[i*2+1].setAttribute('stroke-dasharray', '1,3'  );
      else
        lines[i*2+1].setAttribute('stroke-dasharray', 'none' );
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
        var thisClass = 'move';
        var style = '';
        if( j == 0 || j == paths[i].path.length-1 ) {style  = 'opacity:0;'; thisClass += 'firstlast'; }
        if( inEdit && j == paths[i].path.length-1 ) style += 'display:none';
        connectionDrag( [g,i,j], canvas.rect( g, x-outset, y-outset, 1+inset+outset, 1+inset+outset, {class:thisClass,style:style} ) ); 
      }
    }
    
  }
  
  function connectionDragMouseDown( event )
  {
    //console.log( 'cDMD', event );
    var classList = this.getAttribute('class').split(' ');
    //console.log( 'cDMD', classList );
    //console.log( 'cDMD', event.data.obj );
      
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
    lastPoint = undefined;
    
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
      that.move( ed.obj[1], -1, pos, false, true );
    } else {
      that.move( ed.obj[1], ed.obj[2], pos, false, false );
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
  
  /**
   * Move the selected point
   * branch: the path number
   * i     : the number of the point (-1 = last point)
   * pos   : the new position
   * freely: if true, ignore line alignment
   * extend: continue connection to pos
   */
  var lastPoint = undefined;
  this.move = function( branch, i, pos, freely, extend )
  {
    // FIXME: convert doring the transition period
    if( ! 'x' in pos ) pos = { x: pos[0], y: pos[1] };
    
    var path = paths[ branch ].path; 
    var orig_pos = origin.outPortPos( originPortNumber );
    var i = parseInt( i );           // force cast
    
    if( i < 0 ) i = path.length - 1;
    //var isLast = (i == paths[ branch ].path.length - 1);
    
    if( freely )
    {
      paths[ branch ].path[ i ] = [ pos.x, pos.y ];
      draw();
      return;
    }
    
    if( extend )
    {
      if( lastPoint === undefined ) lastPoint = [ path[ i ][0], path[ i ][1] ];
      while( path.length > lastFixed+1 )
        path.pop();
      i = path.length - 1;
      var dir = 0; // 0 = lr, 1 = td, 2 = rl, 3 = dt
      if( path[i-1] !== undefined )
      {
        if( Math.abs( path[i-1][0] - path[i][0] ) < 1.0 ) // vertical
        {
          if( path[i-1][1] < path[i][1] )
            dir = 1;
          else
            dir = 3;
        } else { // assume horizontal
          if( path[i-1][0] < path[i][0] )
            dir = 0;
          else
            dir = 2;
        }
      } else { // this is the staring point => query block!
        // FIXME - implement!
        path[1] = [ path[0][0], path[0][1] ]; i++;
      }
      //console.log( 'extend', dir, i, path.length, lastFixed, path, lastPoint );
      var op = overPort;
      var prePos = undefined;
      if( op && op.type == 'inPort' )
      {
        pos    = op.block.inPortPos( op.number )[1];
        prePos = op.block.inPortPos( op.number )[0];
        paths[branch].target = op;
      } else
        paths[branch].target = undefined;
      
      switch( dir )
      {
        case 0:
          if( pos.x < lastPoint[0] )
          {
            path[i][0] = lastPoint[0];
            path.push( [ lastPoint[0], pos.y ] );
          } else
            path[i][0] = pos.x;
          break;
          
        case 1:
          if( pos.y < lastPoint[1] )
          {
            path[i][1] = lastPoint[1];
            path.push( [ pos.x, lastPoint[1] ] );
          } else
            path[i][1] = pos.y;
          break;
          
        case 2:
          if( pos.x > lastPoint[0] )
          {
            path[i][0] = lastPoint[0];
            path.push( [ lastPoint[0], pos.y ] );
          } else
            path[i][0] = pos.x;
          break;
          
        case 3:
          if( pos.y > lastPoint[1] )
          {
            path[i][1] = lastPoint[1];
            path.push( [ pos.x, lastPoint[1] ] );
          } else
            path[i][1] = pos.y;
          break;
      }
      path.push( [ pos.x, pos.y ] );
      if( prePos )
        path.push( [ prePos.x, prePos.y ] );
    } else {
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
    }
    // simplify path, i.e. delete double points
    for( var j = path.length-1; j > 0; j-- )
    {
      if( i == j || i == j-1 ) continue; // don't delete current point
      if( Math.abs( path[j-1][0] - path[j][0] ) < 1.0 &&
          Math.abs( path[j-1][1] - path[j][1] ) < 1.0 )
        {
          path.splice( j-1, 2 );
          //if( j < i ) ed.obj[2] -= 2;
        }
    }
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

