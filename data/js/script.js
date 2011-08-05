$(document).ready(function()
	{
		$('#artist_table').dataTable(
			{
				"aoColumnDefs": [
					{ "bSOtrable": false, "aTargets": [ 1 ] } ],
				"bStateSave": true,
				"iDisplayLength": 50,
				"sPaginationType": "full_numbers",
				
			});
	});