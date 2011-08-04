$(document).ready(function()
	{
		$('#artist_table').dataTable(
			{
				"bStateSave": true,
				"iDisplayLength": 50,
				"sPaginationType": "full_numbers",
			});
	});