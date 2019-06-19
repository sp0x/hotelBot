# Example python project

All python projects need to have a `requirements.txt` file with all packages and their versions.  
After you're done with your writing, run `pipreqs --force .`
in order to create a new `requirements.txt` file with all package versions specified.

If you don't have pipreqs, install it with `pip install pipreqs`.

Next you need to create a `Dockerfile` which would describe your service's runtime environment.
Make sure you install all the libraries that are required and the needed python packages.
See the example Dockerfile that's provided.

In order to deploy to our network you'll need to get the `sup` tool.
Ask one of the devs for a compiled binary or install go and run `go install github.com/sp0x/sup`.    
Create a `Supfile.yml` file which would describe the deployment commands, scripts and networks.

You might also want to create a docker-build.sh script to build and push your container.  
This example is using a custom docker registry.  
To try out a deployment run `sup -key <your_id_rsa_key_path> stg deploy`
After it's finished try opening the url for the app.

## Notes:
On windows it's best to use Cygwin, Bash from Mingw64 or WSL, since sup needs bash.
On other platforms you can use your default terminal.


# Running the project locally
Beware that any source code changes need a new build!
To build the bot run `sup local local_build` to build.    
To train the bot run `sup local train`  
To start a debug shell `sup local debug` or if you're on windows
debug.bat and then python main.py 


# Networking
Viber requires the bot have an internet facing url with https.  
You can specify that in the VIBER_HOSTNAME environment variable.  
All events from viber are sent to that url.
Make sure it points to the bot. You might use Nginx with proxy_pass to help you out.