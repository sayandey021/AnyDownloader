import requests

url = "https://cdn-prod-ccv.adobe.com/MoXdMUY5M74/rend/master.m3u8?hdnts=st%3D1781440936%7Eexp%3D1781700136%7Eacl%3D%2Fshared_assets%2Fimage%2F*%21%2Fz%2FMoXdMUY5M74%2Frend%2F*%21%2Fi%2FMoXdMUY5M74%2Frend%2F*%21%2FMoXdMUY5M74%2Frend%2F*%21%2FMoXdMUY5M74%2Fimage%2F*%21%2FMoXdMUY5M74%2Fcaptions%2F*%7Ehmac%3D177f2cc7bf44f10592c7de07d216d747385eaf37b0e449f1cb97e5aa5854de3a"

r = requests.get(url)
print(r.text[:1000])
