window.log = function(){
  log.history = log.history || [];  
  log.history.push(arguments);
  arguments.callee = arguments.callee.caller;  
  if(this.console) console.log( Array.prototype.slice.call(arguments) );
};
(function(b){function c(){}for(var d="assert,count,debug,dir,dirxml,error,exception,group,groupCollapsed,groupEnd,info,log,markTimeline,profile,profileEnd,time,timeEnd,trace,warn".split(","),a;a=d.pop();)b[a]=b[a]||c})(window.console=window.console||{});

jQuery.fn.dataTableExt.oSort['title-string-asc']  = function(a,b) {
	var x = a.match(/title="(.*?)"/)[1].toLowerCase();
	var y = b.match(/title="(.*?)"/)[1].toLowerCase();
	return ((x < y) ? -1 : ((x > y) ?  1 : 0));
};

jQuery.fn.dataTableExt.oSort['title-string-desc'] = function(a,b) {
	var x = a.match(/title="(.*?)"/)[1].toLowerCase();
	var y = b.match(/title="(.*?)"/)[1].toLowerCase();
	return ((x < y) ?  1 : ((x > y) ? -1 : 0));
};

jQuery.fn.dataTableExt.oSort['title-numeric-asc']  = function(a,b) {
	var x = a.match(/title="*(-?[0-9]+)/)[1];
	var y = b.match(/title="*(-?[0-9]+)/)[1];
	x = parseFloat( x );
	y = parseFloat( y );
	return ((x < y) ? -1 : ((x > y) ?  1 : 0));
};

jQuery.fn.dataTableExt.oSort['title-numeric-desc'] = function(a,b) {
	var x = a.match(/title="*(-?[0-9]+)/)[1];
	var y = b.match(/title="*(-?[0-9]+)/)[1];
	x = parseFloat( x );
	y = parseFloat( y );
	return ((x < y) ?  1 : ((x > y) ? -1 : 0));
};

function toggle(source) {
  checkboxes = document.getElementsByClassName('checkbox');
  for(var i in checkboxes)
    checkboxes[i].checked = source.checked;
}