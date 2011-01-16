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
    north__closable: false,
    north__resizable: false
  });
  $('#structureTree').jstree({
    plugins : [ 'json_data', 'themes', 'types' ],
    json_data : {
      data : [
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
        }
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
      }
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
});

function drawLibrary()
{
  $.each( libJSON, function( libName ){
    var lib = $('<div class="lib"><div class="libName">'+libName+'</div></div>');
    $.each( this, function( element ){
      var entry =  $('<div class="libEntry"><div class="libEntryName">'+element+'</div></div>');
      var obj = this;
      var width = this.width+16;
      var height = this.height+6;
      entry.prepend( 
        $('<div style="width:'+width+'px;height:'+height+'px;" ></div>').
        svg({onLoad:function(svg){drawElement(svg,obj,false);},settings:{width:width,height:height}}).
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

var blockRegistry = [];

function drawElement( svg, element, addEvent ){
  if( addEvent === undefined ) addEvent = true;
  var b = new Block( element, svg, addEvent );
  if( addEvent ) blockRegistry.push( b );
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
  var editor = $('#editor');
  var svg    = $('#editor svg')[0];
  svg.width.baseVal.value = Math.max( maxX, editor.innerWidth() );
  svg.height.baseVal.value = Math.max( maxY, editor.innerHeight() );
}

jQuery(document).ready(function(){
  getCoordinate = (function()
  {
    var editor = $('#editor');  // quasi static variable
    return function( event ) {
      var o = editor.offset();
      return {x: event.pageX - o.left + editor.scrollLeft(),
              y: event.pageY - o.top  + editor.scrollTop () };
    };
  })();
});

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
  var editor = $('#editor');  // quasi static variable
  var svg    = $('#editor svg')[0];
  var x = Math.max( maxX, editor.innerWidth() );
  var y = Math.max( maxY, editor.innerHeight() );
  var factor = Math.pow(Math.sqrt(2),10-zoomLevel);// Math.log(-10+zoomLevel) / Math.log( 2 );
  if( zoomLevel < 10 )
  {
    svg.width.baseVal.value    = x* factor;
    svg.height.baseVal.value   = y* factor;
    svg.viewBox.baseVal.width  = x;
    svg.viewBox.baseVal.height = y;
  } else {
    svg.width.baseVal.value    = x;
    svg.height.baseVal.value   = y;
    svg.viewBox.baseVal.width  = x / factor;
    svg.viewBox.baseVal.height = y / factor;
  }
}