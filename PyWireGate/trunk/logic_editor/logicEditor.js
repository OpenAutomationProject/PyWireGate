/* logicEditor.js (c) 2011 by Christian Mayer [CometVisu at ChristianMayer dot de]
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

//console.log = function(){}; // global disable of debug messages

// global variables
var overPort = false;
var connectionLookingForInPort = true; // only relevant in connection drawing mode
var maxX = 0; // the biggest x value of the current view
var maxY = 0; // the biggest y value of the current view
var zoomLevel = 10; // 1 = biggest, +inf = smallest

$(function() {
  $('body').layout({ 
    applyDefaultStyles: false,
    center__onresize: function( name, element, state ){
      var editor = element.find('svg')[0];
      editor.width.baseVal.value = Math.max( maxX, state.innerWidth );
      editor.height.baseVal.value = Math.max( maxY, state.innerHeight );
    },
    north__closable : false,
    north__resizable: false,
    south__closable : false,
    south__resizable: false
  });
  $('#structureTree').bind("select_node.jstree", function (event, data) {
    displayLogic( $.trim( $(data.args[0]).text() ) );
  }).jstree({
    plugins : [ 'json_data', 'themes', 'types', 'ui' ],
    json_data : {
      data : [/*
        {
          data : 'System 1',
          attr : { rel : 'logic' },
          children : [ 
          {
            data: 'Subsystem 1',
            attr: { rel: 'subsystem' },
            children : [
            {
              data: 'Subsubsystem',
              attr: { rel: 'subsystem' }
              }
            ]
            },
            'Subsystem 2',
            'Subsystem 3' 
          ]
        },
        {
          attr : { rel : 'logic' },
          data : {
            title : 'System 2',
            attr : { href : "#" }
          }
        }*/
      ]
    },
    themes: {
      theme: 'classic',
      dots : true,
      icons: true
    },
    types: {
      types: {
        logic    : { icon: { image: 'icon/16/code-block.png' } },
        subsystem: { icon: { image: 'icon/16/code-block.png' } }
      },
    },
    'ui' : {
      'select_limit' : 1,
      'selected_parent_close' : 'select_parent'
    }
  });
  
  // prevent the toolbar images to be dragged around
  $('img.toolbarButton').bind('dragstart', function(event) { event.preventDefault(); });
  
  drawLibrary();
  $('#editor').svg().
    droppable({drop: editorDrop}).
    bind('mousedown',function(){
      $('.selected').each(function(){
        this.setAttribute( 'class', this.getAttribute( 'class' ).replace( 'selected', '' ) );
      });
    });
  var svg = $('#editor').svg('get');
  var defs = svg.defs();
  var marker = svg.marker( defs, 'ArrowEnd', 0.0, 0.0, 10, 10, 'auto', {style:'overflow:visible'} );
  var path = svg.createPath();
  svg.path( marker, path.
    move(-10.0, 0.0).
    line(-15.0,-4.0).
    line(  0.0, 0.0).
    line(-15.0, 4.0).
    line(-10.0, 0.0).
    close()
  );
  marker = svg.marker( defs, 'EmptyInPort', 0.0, 0.0, 10, 10, 'auto', {style:'overflow:visible'} );
  var path = svg.createPath();
  svg.path( marker, path.
    move(-5.0,-5.0).
    line( 0.0, 0.0).
    line(-5.0, 5.0).
    close()
  );
  marker = svg.marker( defs, 'EmptyOutPort', 0.0, 0.0, 10, 10, 'auto', {style:'overflow:visible'} );
  var path = svg.createPath();
  svg.path( marker, path.
    move( 0.0,-5.0).
    line( 5.0, 0.0).
    line( 0.0, 5.0).
    close()
  );
  
  $(document).bind('keydown', 'del', function(){ $('.selected').remove(); });
});

function drawLibrary()
{
  $.each( libJSON, function( libName ){
    var lib = $('<div class="lib"><div class="libName">'+libName+'</div></div>');
    $.each( this, function( element ){
      var entry =  $('<div class="libEntry"></div>');
      var obj = this;
      obj.type = libName + '/' + element;
      var width = this.width+20;
      var height = this.height+35;
      entry.prepend( 
        $('<div style="width:'+width+'px;height:'+height+'px;" ></div>').
        svg({onLoad:function(svg){drawElement(svg,obj,false);},settings:{width:width,height:height,viewBox:'-10 -10 '+width+' '+height}}).
        data( 'element', obj ).
        draggable({helper: function (e,ui) {
          return $(this).clone().appendTo('body').css('zIndex',5).show();
        }} )
      );
      lib.append( entry );
    });
    $('#library').append( lib );
  });
}

function updateKnownLogics( newLogicName )
{
  $('#structureTree').jstree('create_node', -1, 'after',  { 
    'data' : newLogicName,
    'attr' : { rel : 'logic'}
  });
}

function displayLogic( logicName )
{
  logic = logics[ logicName ];
  
  $('#editor g').remove(); // clean canvas first
  blockRegistry = {};      // and then the block registry
  
  // draw all the blocks
  $.each( logic.blocks, function( name, def ){
    var type = def.type.split('/');
    var newBlock = $.extend( true, {}, libJSON[ type[0] ][ type[1] ], def, {'name':name} );
    drawElement( undefined, newBlock, true );
  });
  
  // and connect them
  $.each( logic.signals, function( name, def ){
    var startBlock = blockRegistry[ def[0] ];
    var endBlock = blockRegistry[ def[2] ];
    var pn = def[1];
    var op = startBlock.outPortPos( pn )[0];
    var ip = endBlock.inPortPos( def[3] )[0];
    var c = new Connection({
      origin          : startBlock,
      originPortNumber: pn,
      paths           : [{path:[ [op.x, op.y], [ip.x, ip.y] ],target:endBlock}]
    });
    startBlock.setConnection( 'outPort', pn, c );
    endBlock.setConnection( 'inPort', def[3], c );
  });
}

var blockRegistry = {};

function drawElement( svg, element, addEvent ){
  if( addEvent === undefined ) addEvent = true;
  var b = new Block( element, svg, addEvent );
  if( addEvent ) blockRegistry[ element.name ] = b;
  // FIXME this should become more generalized
  if( 'MainLib/display' == element.type || 'MainLib/scope' == element.type ) // make display and scope interactive
  {
    liveUpdateCalls.push( [
      b.getName(),
      'MainLib/display' == element.type,
      b._updateValue
    ] );
  }
}

function colorByArray( a )
{
  return 'rgb(' + 
    (a[0]*255).toFixed() + ',' +
    (a[1]*255).toFixed() + ',' +
    (a[2]*255).toFixed() + ')';
}

function editorDrop( event, ui )
{
  if( ui.draggable.data('element') )
  {
    var c = getCoordinate( {pageX: ui.position.left, pageY: ui.position.top} );
    var data = $.extend( true, c, ui.draggable.data('element') );
    drawElement( $('#editor').svg('get'), data );
    editorResize( { x: c.x + data.width, y: c.y + data.height } );
  }
}

function editorSelect( element )
{
  $('.selected').each(function(){
    this.setAttribute( 'class', this.getAttribute( 'class' ).replace( 'selected', '' ) );
  });
  element.setAttribute( 'class', element.getAttribute( 'class' ) + ' selected' );
}

/**
 * Iterate over all blocks to make sure the editor is big enough
 * The optional parameter "test" allows to bypass the resize if it's not
 * necessary, i.e. the test.{xy} fits into the current canvas
 */
function editorResize( test )
{
  var extraSpace = 20; // a bit more space, e.g. for scroll bars
  
  if( test !== undefined &&
      test.x + extraSpace <= maxX && test.y + extraSpace <= maxY )
    return;
  
  maxX = 0;
  maxY = 0;
  $.each( blockRegistry, function(){
    var x = this.getX() + this.getWidth();
    var y = this.getY() + this.getHeight();
    if( x > maxX ) maxX = x;
    if( y > maxY ) maxY = y;
  });
  maxX += extraSpace; maxY += extraSpace;
  zoomEditor( 0 ); // resize with current zoom level
}

jQuery(document).ready(function(){
  getCoordinate = (function()
  {
    var editor = $('#editor');  // quasi static variable
    return function( event ) {
      var o = editor.offset();
      var factor = zoomFactor();
      return {x: (event.pageX - o.left + editor.scrollLeft()) / factor,
              y: (event.pageY - o.top  + editor.scrollTop ()) / factor};
    };
  })();
});

/**
 * Calculate the current zoom factor
 * a zoom factor of 10 equals 100%
 */
function zoomFactor()
{
  return Math.pow( Math.sqrt(2), 10-zoomLevel );
}

/**
 * Zoom the editor canvas.
 * level == -1 : zoom out
 * level ==  0 : NOP
 * level == +1 : zoom in
 * level > 1 : zoom to that value, 10 = 100% = 1:1
 */
function zoomEditor( level )
{
  if( level > 1 )
    zoomLevel = level;
  else
    zoomLevel -= level;
  zoomLevel = zoomLevel < 0 ? 0 : zoomLevel; // limit to huge 3200%
  
  var editor = $('#editor');  // quasi static variable
  var svg    = $('#editor svg')[0];
  var x = Math.max( maxX, editor.innerWidth() );
  var y = Math.max( maxY, editor.innerHeight() );
  var factor = zoomFactor();
  $('#zoomLevel').html( (100*factor).toFixed() + '%' );
  if( factor > 1 )
  {
    svg.width.baseVal.value    = x * factor;
    svg.height.baseVal.value   = y * factor;
    svg.viewBox.baseVal.width  = x;
    svg.viewBox.baseVal.height = y;
  } else {
    svg.width.baseVal.value    = x;
    svg.height.baseVal.value   = y;
    svg.viewBox.baseVal.width  = x / factor;
    svg.viewBox.baseVal.height = y / factor;
  }
}

////////////////////////
// FIXME - delete it later, this are just helpers for debugging
function _showEvents( target, doLog )
{
  var count = 0;
  jQuery.each($(target || '*'), function(j,element){
    //console.log( j, this );
    var that = this;
    var d = $(this).data();
    if( d.events )
    {
      console.log( count, element );
      jQuery.each( d.events, function( i, handler ){
        //console.log( j, i, handler[0].handler.toString() );
        console.log( count, i, handler[0].handler );
        if( doLog )
        {
          $(element).bind( i, function(){} );
        }
      });
      count++;
    }
  });
}