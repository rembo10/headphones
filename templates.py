_header = '''
	<html>
	<head>
		<title>Headphones</title>
		<link rel="stylesheet" type="text/css" href="data/css/style.css" />
		<link rel="icon" type="image/png" href="data/images/headphoneslogo.png" />
		<link rel="apple-touch-icon" href="data/images/headphoneslogo.png" />
	</head>
	<body>
	<div class="container">'''
			
_logobar = '''
		<div class="logo"><a href="/"><img src="data/images/headphoneslogo.png">headphones</div><a>
			<div class="search"><form action="findArtist" method="GET" align="right">
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
					<a href="/shutdown"><font color="red">SHUTDOWN</font></a>
			</div>'''
	
_footer = '''
	</div><div class="footer"></div>
	</body>
	</html>'''