from headphones import web_root

_header = '''
	<html>
	<head>
		<title>Headphones</title>
		<link rel="stylesheet" type="text/css" href="data/css/style.css" />
		<link rel="icon" type="image/x-icon" href="data/images/favicon.ico" /> 
		<link rel="apple-touch-icon" href="data/images/headphoneslogo.png" />
	</head>
	<body>
	<div class="container">'''
			
_logobar = '''
		<div class="logo"><a href=""><img src="data/images/headphoneslogo.png" border="0">headphones<a></div>
			<div class="search"><form action="findArtist" method="GET">
			<input type="text" value="Add an artist" onfocus="if
			(this.value==this.defaultValue) this.value='';" name="name" />
			<input type="submit" /></form></div><br />
	'''

_nav = '''<div class="nav">
					<a href="">HOME</a>
					<a href="upcoming">UPCOMING</a>
					<a href="manage">MANAGE</a>    
					<a href="history">HISTORY</a>
					<a href="config">SETTINGS</a>
					<div style="float:right">
					  <a href="restart" title="Restart"><img src="data/images/restart.png" height="15px" width="15px"></a>
					  <a href="shutdown" title="Shutdown"><img src="data/images/shutdown.png" height="15px" width="15px"></a>
					</div>
			</div>'''
	
_footer = '''
	</div><div class="footer"><br /><div class="center"><form action="https://www.paypal.com/cgi-bin/webscr" method="post">
<input type="hidden" name="cmd" value="_s-xclick">
<input type="hidden" name="hosted_button_id" value="93FFC6WDV97QS">
<input type="image" src="https://www.paypalobjects.com/en_US/i/btn/btn_donate_SM.gif" border="0" name="submit" alt="PayPal - The safer, easier way to pay online!">
<img alt="" border="0" src="https://www.paypalobjects.com/en_US/i/scr/pixel.gif" width="1" height="1">
</form>
</div></div>
	</body>
	</html>'''