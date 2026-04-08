FROM python:3.10
# Set the default shell to bash
SHELL ["/bin/bash","-c"]
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# COPY docker docker

# COPY ai/estimate-weeding-areas-from-ndvi/estimate-weeding-areas-from-apa ai/estimate-weeding-areas-from-ndvi/estimate-weeding-areas-from-apa
# RUN docker/install_area_of_interest_detectors_based_on_gnss.sh

#RUN echo "flask --app main.py run --cert=cert.pem --key=key.pem --host=0.0.0.0" > /usr/bin/start.sh
#RUN chmod +x /usr/bin/start.sh
EXPOSE 5000
#ENTRYPOINT '/usr/bin/start.sh'

COPY . .
CMD ["flask", "--app",  "main.py", "run", "--cert=cert.pem", "--key=key.pem", "--host=0.0.0.0"]
#CMD ["flask", "--app",  "main.py", "run", "--host=0.0.0.0"]
