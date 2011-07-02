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
		<div class="logo"><a href="/"><img src="data/images/headphoneslogo.png" border="0">headphones<a></div>
			<div class="search"><form action="findArtist" method="GET">
			<input type="text" value="Add an artist" onfocus="if
			(this.value==this.defaultValue) this.value='';" name="name" />
			<input type="submit" /></form></div><br />
	'''

_nav = '''<div class="nav">
					<a href="/">HOME</a>
					<a href="/upcoming">UPCOMING</a>
					<a href="/manage">MANAGE</a>    
					<a href="/history">HISTORY</a>
					<a href="/config">SETTINGS</a>
					<div style="float:right">
					  <a href="/restart"><img src="data/images/restart.png" height="15px" width="15px"></a>
					  <a href="/shutdown"><img src="data/images/shutdown.png" height="15px" width="15px"></a>
					</div>
			</div>'''
	
_footer = '''
	</div><div class="footer"></div>
	</body>
	</html>'''