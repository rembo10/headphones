# About less and css

**The main message of this document: DO NOT MODIFY style.css - IT IS GENERATED FILE**

----

If you want modify the appearance of Headphones, please, follow this simple steps.

0. **Install**. Do this just once, and if you still do not have `lessc` utility on your PC. Here is very useful guide, how to install less : [http://lesscss.org/#using-less-installation](http://lesscss.org/#using-less-installation)
1. **Modify**. Carefully add your changes to the `style.less` (`.less` extension, not `.css`).
2. **Compile**. Currently, there is no magic, so you should compile css manually. Go to the `/data/interfaces/default/css` folder (or use full paths..), and then just type:

```bash
lessc style.less > style.css
```

_works good on *nix hosts, I didn't test this on win-hosts_

DONE. You have new CSS file.

## LESS

Less is very useful tool (CSS pre-processor) for CSS writing. There is the awesome guide on the official site: [Official Less Guide](http://lesscss.org/features/)

Thanks!