# invoice-generator
A web application to generate PDF invoices from CSV file contents using Python Flask, Docker, Google Cloud Platform and Firebase.

## Features
- Upload CSV files containing invoice data.
- Generate PDF invoices from the uploaded data.
- Deploy easily with Docker on Google Cloud Platform.
- Host the web application on Firebase.

## Preview
URL : https://invoice.moonstar.com.np

## Technologies Used

- **Python** and **Flask** for the main application logic and web server.
- **Docker** for containerization.
- **Google Cloud Platform** for deployment.
- **Firebase** for web hosting.

## Installation

1. **Clone the repository:**

    ```bash
    git clone https://github.com/yourusername/invoice-generator.git
    ```

2. **Change to the project directory:**

    ```bash
    cd invoice-generator
    ```

3. **Add secrets:**

    Create a `.env` file in the project root directory and add the following secrets:

    ```bash
    Flask_SECRET_KEY=your_secret_key
    ```
    Replace `your_secret_key` with a secret key of your choice.

4. **Initialize Firebase:**

    - Create a Firebase project from the [Firebase Console](https://console.firebase.google.com/).
    - Change the project plan to Blaze (Pay as you go).
    - Install Firebase CLI:

        ```bash
        npm install -g firebase-tools
        ```

    - Login to Firebase and initialize Firebase:

        ```bash
        firebase login
        ```
        ```bash
        firebase init
        ```
    
    - Select your newly created Firebase project *(Use an existing project).*
    - During feature selection, choose Hosting.
        - Hosting Setup: Public directory: `public`, Single-page app: `No`
        
5. **Setup Google Cloud Platform:**

    - Install Google Cloud SDK : https://cloud.google.com/sdk/docs/install

    - Initialize GCP and set project:
        ```bash
        gcloud init
        ```
        ```bash
        gcloud config set project <your-project-id>
        ```
        `Note:` Replace `<your-project-id>` with your firebase project id.

    - Build and submit Docker image:
        ```bash
        gcloud builds submit --tag gcr.io/<your-project-id>/invoice-generator
        ```
    - Deploy to Cloud Run:
        ```bash
        gcloud run deploy invoice-generator \
            --image gcr.io/<your-project-id>/invoice-generator \
            --platform managed \
            --region us-central1 \
            --allow-unauthenticated
        ```
        `Note:` Replace `<your-project-id>` with your firebase project id and `us-central1` with your preferred region (optional).

6. **Configure Firebase Hosting and Run the App:**
    - Edit `firebase.json` file to include the rewrite configuration:
        ```json
        {
            "hosting": {
                "public": "public",
                "rewrites": [
                    {
                    "source": "**",
                    "run": {
                        "serviceId": "invoice-generator",
                        "region": "us-central1"
                    }
                    }
                ]
            }
        }
        ```
        `Note:` Replace `us-central1` with your preferred region (optional).
    
    - Deploy to Firebase Hosting:
        ```bash
        firebase deploy --only hosting
        ```

    - Your app will be available at:
        ```
        https://<your-project-id>.web.app
        ```
        `Note:` You can also use a custom domain by connecting a domain to Firebase Hosting. For that go to Firebase Console > Hosting > Connect Custom Domain.
    
## Contact
Email : manoj.shrestha8080@gmail.com

## License
This project is licensed under GNU General Public License.