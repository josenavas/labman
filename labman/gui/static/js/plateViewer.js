/**
 *
 * @class PlateViewer
 *
 * Shows the plate information
 *
 * @param {int} plateId The plate id
 * @param {string} target The name of the target container for the plate viewer
 *
 * @return {PlateViewer}
 * @constructs PlateViewer
 *
 **/
function PlateViewer(plateId, target) {
  var that = this;

  this.plateId = plateId;
  this.target = $('#' + target);

  // Retrieve plate information from the server
  $.get('/plate_layout?plate_id=' + this.plateId, function (data) {
    that.initialize(data);
  })
    .fail(function (jqXHR, textStatus, errorThrown) {
      that.target.append(jqXHR.responseText);
    });
};

/**
 *
 * Initializes the interface with the plate information
 *
 * @param {Object} data The data returned from the GET query
 *
 */
PlateViewer.prototype.initialize = function (data) {
  var $table, $row, $col, rowId;

  // Store the plate information
  this.rows = data.rows;
  this.cols = data.cols;
  this.editable = data.editable;
  this.inputTags = new Array(this.rows);
  for (var i = 0; i < this.rows; i++) {
    this.inputTags[i] = new Array(this.cols);
  }

  // Draw the table that represents the plate
  $table = $('<table>');
  $table.appendTo(this.target);

  // Add the header row
  $row = $('<tr>');
  $row.appendTo($table);
  $('<th>').appendTo($row);
  for (var i = 0; i < this.cols; i++) {
    $col = $('<th>');
    $col.attr('style', 'text-align: center;')
    $col.html(i+1);
    $col.appendTo($row);
  }

  // Adding the rest of the rows
  rowId = 'A'
  for (var i = 0; i < this.rows; i++) {
    $row = $('<tr>');
    $row.appendTo($table);
    $col = $('<th>');
    $col.html(rowId);
    rowId = formatRowId(rowId)
    $col.appendTo($row);
    // Adding the rest of the rows
    for (var j = 0; j < this.cols; j++) {
      $col = $('<td>');
      $col.appendTo($row);
      $well = this.constructWell(i, j);
      $well.appendTo($col);
    }
  }
};

PlateViewer.prototype.constructWell = function(row, column) {
  var that = this;
  // Div holding well
  var $d = $('<div>');
  // The input tag
  var $i = $('<input>');
  $i.attr('pv-well-row', row).attr('pv-well-column', column).attr('type', 'text').attr('size', 15);
  $i.attr('disabled', !this.editable);

  // Add the different callbacks
  $i.keypress(function(e) {
    if (e.which === 13) {
      // The user hit enter, which means that we have to move down one row
      // Retrieve which is the current row and column
      var row = parseInt($(this).attr('pv-well-row'));
      var col = parseInt($(this).attr('pv-well-column'));
      // Update indices
      row = row + 1;
      if (row === that.rows) {
        row = 0;
        col = col + 1;
        if (col === that.cols) {
          col = 0;
        }
      }
    }
    // Set the focus to the next input tag
    that.inputTags[row][col].focus();
  });

  $i.focusin(function(e) {
    // When the input element gets focus, store the current indices to be able
    // to add the comments to this specific well
    $('#comment-modal-btn').attr('pv-row', parseInt($(this).attr('pv-well-row')));
    $('#comment-modal-btn').attr('pv-col', parseInt($(this).attr('pv-well-column')));
  });

  $i.change(function(e) {
    // Todo - what happens when the value changes
  });

  $i.appendTo($d);

  this.inputTags[row][column] = $i;
  return $d;
};

/**
 *
 * Formats the row Id
 * Adapted from: https://stackoverflow.com/a/34483399
 *
 * @param {int} row The row number
 *
 * @return {string}
 *
 **/
function formatRowId(row) {
  var u = row.toUpperCase();
  if (sameStrChar(u,'Z')) {
    var txt = '';
    var i = u.length;
    while (i--) {
      txt += 'A';
    }
    return (txt+'A');
  } else {
    var p = "";
    var q = "";
    if(u.length > 1){
      p = u.substring(0, u.length - 1);
      q = String.fromCharCode(p.slice(-1).charCodeAt(0));
    }
    var l = u.slice(-1).charCodeAt(0);
    var z = nextLetter(l);
    if(z==='A'){
      return p.slice(0,-1) + nextLetter(q.slice(-1).charCodeAt(0)) + z;
    } else {
      return p + z;
    }
  }
};

function nextLetter(l){
  if(l<90){
    return String.fromCharCode(l + 1);
  }
  else{
    return 'A';
  }
}

function sameStrChar(str,char){
  var i = str.length;
  while (i--) {
    if (str[i]!==char){
      return false;
    }
  }
  return true;
}
