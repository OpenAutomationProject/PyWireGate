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
  var g = undefined; // link to the representation of the block in the DOM
  
  // the private functions
  
  // (re)draw itself on the canvas
  function draw()
  {
    var classList = 'connection';
    if( g ) 
    {
      classList = g.getAttribute('class');
      g.parentNode.removeChild( g ); // delete the old representation
    }
    g = canvas.group( { 'class':classList } );

    var parameter = {
      class: classList,
      stroke: colorByArray( origin.getColor() ),
      'stroke-width': 1, 
      'marker-end'  : 'url(#ArrowEnd)',
      fill:  'none'
    };
    for( var i in paths )
    {
      if( paths[i].target == undefined || origin == undefined )
        parameter['stroke-dasharray'] = '1,3';
      else
        parameter['stroke-dasharray'] = 'none';
      var x = canvas.polyline( g, paths[i].path, parameter );
    }
  }
  
  this.firstMove = function( pos )
  {
    if( paths[0].path[0][1] == paths[0].path[1][1] ) // keep horizontal line
    {
      paths[0].path[0] = pos;
      paths[0].path[1][1] = pos[1];
    } else {
      paths[0].path[0] = pos;
    }
    draw();
  }
  
  this.lastMove = function( pos, force )
  {
    while( paths[branch].path.length > lastFixed+1 )
      paths[branch].path.pop();
    var start = paths[branch].path[ paths[branch].path.length - 1 ];
    var op = overPort;
    if( !force && op && op.type == 'inPort' )
    {
      pos = op.block.inPortPos( op.number );
    }
    if( force || (op && op.type == 'inPort') )
    {
      paths[branch].target = op;
      if( Math.abs( start[1] - pos[1] ) > 1.0 )
        paths[branch].path.push( [ (pos[0]+start[0])/2, start[1] ] );
      paths[branch].path.push( [ (pos[0]+start[0])/2, pos[1] ] );
    } else {
      paths[branch].target = undefined;
      if( Math.abs( start[1] - pos[1] ) > 1.0 )
        paths[branch].path.push( [ pos[0], start[1] ] );
    }
    paths[branch].path.push( pos );
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

