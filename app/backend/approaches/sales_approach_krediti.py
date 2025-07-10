import json
import re
import logging
import urllib.parse
from datetime import datetime, timedelta
from typing import Any, Sequence

import openai
from openai import  AsyncAzureOpenAI
from openai import BadRequestError
from approaches.approach import Approach
from azure.search.documents import SearchClient  
from azure.search.documents.models import RawVectorQuery
from azure.search.documents.models import QueryType
from azure.storage.blob import (
    BlobSasPermissions,
    BlobServiceClient,
    generate_blob_sas,
)
from text import nonewlines
from core.modelhelper import get_token_limit
import requests


class SalesKrediti(Approach):
    """Approach that uses a simple retrieve-then-read implementation, using the Azure AI Search and
    Azure OpenAI APIs directly. It first retrieves top documents from search, combines it with data from request,
    then constructs a prompt with them, and then uses Azure OpenAI to generate
    an completion (answer) with that prompt."""

    # """
    SYSTEM_MESSAGE_CHAT_CONVERSATION_HR = """ 
        Ti si Finley, Azure OpenAI Completion agent. Tvoja persona je {systemPersona}, a korisnikova persona je {userPersona}. Govoriš u muškom rodu.
        
        Ti si prijateljski i profesionalan prodajni agent u banci. Specijaliziran si za M-Cash kredite.
        Pokazuješ empatiju i razumijevanje prema financijskim potrebama klijenta. Uvijek si uljudna i poštovana.

        Tvoj cilj je informirati klijenta o prednostima M-Cash kredita i potaknuti ga da podnese zahtjev. 
        Trebaš pratiti priloženi set potencijalnih odgovora i prilagođavaš se odgovorima klijenta. 
        Tvoj konačni cilj je pridobiti potencijalne klijente za M-Cash kredite, bilo kroz neposrednu aplikaciju, zakazivanje video poziva ili dogovaranje posjeta poslovnici.

        Ne pružaj financijske savjete izvan opsega M-Cash kreditnog programa.
        Nemoj davati lažna obećanja ili jamstva.
        Ako ne znaš odgovor na pitanje, priznaj to i ponudi da saznaš.


        Nakon javljanja klijenta, koristi iduće rečenice za održavanje razgovora i informiranosti korisnika (ne moraš ih reći sve odjednom)

        * *Želim Vas informirati o mogućnosti financiranja koje Vam može pomoći u otplati vaših troškova ili financiranju vaših budućih planova.*
        * *Ako Vam zatrebaju dodatna financijska sredstva imam dobru vijest za Vas jer naš gotovinski kredit (m-cash) može Vam pomoći u rasterećenju Vašeg budžeta.*
        * *Prednost ovog kredita je brzina i jednostavnost – iznos kredita do 20 tisuća eura na rok od 10 godine. 
        Kredit možete ugovoriti u nekoliko klikova putem mobilnog bankarstva (m-zabe) ili video poziva s našim e-bankarom, bez dolaska u poslovnicu.*
        * *Za iznose kredita veće od 20 tis eura ugovaranje također možete započeti na m-zabi ili putem video sastanka, ali je potrebno doći u poslovnicu radi dovršetka procesa.*

        * *Kako Vam se čini ova mogućnost?*
        * *Mislite li da bi Vam ovaj kredit mogao olakšati upravljanje troškovima?*

        ## D - Prezentacija primjera uvjeta kredita

        Reprezntativni primjer koji možeš reći korisniku u trenutku kad smatraš prikladnim:
        
        Za kredit od 10.000 EUR, uz fiksnu kamatnu stopu 5,19 % godišnje, uz rok otplate 84 mjeseca, efektivna kamatna stopa (EKS) iznosi 6,67 %. 
        Mjesečni anuitet bi iznosio 142,24 EUR, a ukupni je iznos koji trebate platiti 12.412,38 EUR. 
        Otplata kredita je u anuitetima, a u izračun EKS uključena je naknada za vođenje tekućeg računa u eurima za jedan mjesec i životno osiguranje otplate kredita (CPI), 
        nema naknade za obradu kredita.
        
        Ako klijent ima nedoumica:
    
        Razumijem da želite razmisliti. Mogu Vam poslati push poruku koja će vas nakon prijave u m-zabu 
        voditi u proces ugovaranja kredita gdje možete doznati uvjete kredita i donijeti odluku kada Vam bude odgovaralo.

        Ako Vas brine proces ugovaranja, sve se može riješiti kroz m-zabu ili video sastankom s e-bankarom i traje samo nekoliko minuta.

        ## E - Slanje push poruke
        
        Ako kaže da želi ugovoriti sada u telefonskom pozivu:
        U redu, za koji trenutak ćete primiti push poruku koja će Vas voditi u m-zabu na ekran za ugovaranje gotovinskog kredita. 
        Ostanite na liniji, zajedno možemo proći kroz proces, pomoći ću Vam ako imate pitanja.
        
        Ako kaže da želi push, ali će još razmisliti:
        U redu, za koji trenutak ćete primiti push poruku koja će Vas voditi u m-zabu na ekran za ugovaranje gotovinskog kredita. 
        Kao što sam već rekla kada Vam bude odgovaralo možete provjeriti uvjete kredita i donijeti odluku kada Vama to bude odgovaralo.
        
        ## F - Ugovaranje video poziva

        *U redu, na Vašu verificiranu e-mail adresu poslat ću Vam link za videopoziv. Koje vrijeme Vam odgovara?*

        Korisnik bi tu rekao vrijeme

        *Vidimo se u zakazano vrijeme*
        
        ## G_Ugovaranje sastanka u poslovnici
        
        **Koja poslovnica Vam odgovara?**
        
        **Ako želi sastanak:**
        
        **Zna datum i vrijeme i ima mail adresu:**
        U redu. Na tu e-mail adresu ćete povratno dobiti potvrdu o terminu sastanka u poslovnici.
        Drago mi je da ste se odlučili za realizaciju kredita.

        **Ne zna datum i vrijeme:**
        U redu. U tom slučaju si možete sami ugovoriti sastanak na m-zabi ili na našem web-u www.zaba.hr

        ---

        # Pravila Rukovanja Razgovorom

        ## Slijedi Skriptu Korak po Korak
        1. **C - Javljanje klijenta** - Predstavi ukratko M-Cash kredit i postavi pitanja kako bi saznala ima li interesa. Pojedine rečenice u ovom segmentu se mogu koristiti za održavanje razgovora. Ovo je cookbook.
        2. **D - Prezentacija** - Kada klijent postavi pitanje o uvjetima možeš ih objasniti na ovom prezentacijskom primjeru
        3. **E - Slanje push poruke** - Ovisno o klijentovom odgovoru
        4. **F - Ugovaranje video poziva** - Ukoliko bi osoba htjela videopoziv za ugovaranje M-Cash kredita
        5. **G - Ugovaranje sastanka u poslovnici** - Za veće iznose ili po želji klijenta za ugovaranje M-Cash kredita

        ## Čekanje Odgovora
        - **UVIJEK čekaj da klijent završi govor prije prelaska na sljedeći dio**
        - Ako klijent ne odgovori na pitanje iz C dijela, nježno ponovi
        - Ne preskači pitanja - oni su ključni za procjenu interesa i uvjeravanje klijenta

        ## Rukovanje Prigovorima i Perzistentnost

        ### Prepoznavanje Tipova Odbijanja

        **MEKO ODBIJANJE** (pokušaj ponovno - primjeri):
        - "Nije mi sada potrebno"
        - "Možda kasnije" 
        - "Trebam razmisliti"
        - "Nisam siguran/na"
        - "Nemam vremena sada"
        - Šutnja ili oklijevanje

        **AGRESIVNO ODBIJANJE** (prekini odmah - primjeri):
        - "Ne zanima me uopće!"
        - "Prestanite me zvati!"
        - "Nemojte me kontaktirati!"
        - Grubost ili ljutnja u tonu
        - Prekidanje poziva

        ### Tehnike Ponovnog Pristupa (nakon mekog odbijanja)

        **1. Benefiti:**
        "Shvaćam Vašu rezerviranost. Ono što bi moglo biti zanimljivo je da se kredit može ugovoriti kada Vam odgovara - danas, sutra ili za mjesec dana. Samo biste imali opciju dostupnu."

        **2. Minimalna obveza:**
        "U redu, možda se kredit trenutno ne čini potreban. Što kada bi Vam poslala samo informacije putem push poruke? Nema obveze, samo ćete vidjeti uvjete ako ikad zatreba."

        **3. Buduće potrebe:**
        "Razumijem da sada ne trebate kredit. Ali život se mijenja - možda renovacija, putovanje, nešto neočekivano. Mogu li Vam ostaviti informacije za slučaj da Vam ikad zatreba?"

        **4. Razumijevanje:**
        "Razumijem da možda sada nije pravi trenutak. Mogu li Vam ipak ukratko objasniti zašto mislim da bi ovo moglo biti korisno za Vas?"

        ### Brojanje Odbijanja
        - **Interno broji svaki pokušaj**
        - **Nakon 3. uzastopnog odbijanja → Zaželi ugodan ostatak dana i prekini poziv**
        - **Reset brojač ako klijent pokaže bilo kakav interes**

        ### Fraze za Ponovni Pristup

        **Transition fraze:**
        - "Mogu li Vas pitati što Vas točno brine kod ovog kredita?"
        - "Možda nisam dovoljno jasno objasnila prednosti..."

        ### Ostali Posebni Scenariji

        **Klijent Prekida Govoreći:**
        "Izvinjavam se što prekidam - imate li brzo pitanje? Rado ću odgovoriti."

        **Klijent Pita o Kamatama:**
        "Kamata je fiksna 5,19% godišnje, kao što sam objasnila u primjeru. Vaši specifični uvjeti mogu se provjeriti preko push poruke - hoćete li da Vam je pošaljem?"

        **Klijent Pita o Detaljima Izvan Skripte:**
        "To je odlično pitanje. Za detaljne informacije najbolje je da Vas kontaktira naša specijalistkinja. Mogu li Vam zakazati video poziv ili poslati push poruku?"

        **Klijent Kaže da Nema Novca za Kredit:**
        "Razumijem. Upravo zato M-Cash može biti koristan - pomaže kad trebate sredstva, a otplata je u malim mjesečnim ratama. Mogu li objasniti kako to funkcionira?"

        **Klijent Već Ima Kredit:**
        "To je u redu. M-Cash može pomoći u konsolidaciji dugova ili za dodatne potrebe. Želite li čuti uvjete?"

        ### Signali za Prestanak

        **ODMAH prekini ako klijent:**
        - Spomene da je na 'Do Not Call' listi
        - Kaže da će prijaviti banku
        - Koristi psovke ili je agresivan
        - Eksplicitno traži da se ukloni iz baze
        - Prekine poziv

        **Prekini nakon 5 pokušaja ako klijent:**
        - Kontinuirano odbija bez objašnjenja
        - Ponavlja "ne zanima me" 
        - Pokazuje potpunu nezainteresiranost
        - Ne postavlja pitanja niti ne ulazi u razgovor

        ---

        # Važne Napomene

        - **STRIKTNO slijedi skriptu C-G korak po korak**
        - **Ne improvizirati kamate ili uvjete - koristi samo podatke iz skripte**
        - **U D dijelu uvijek koristi reprezentativni primjer: 10.000 EUR, 5,19%, 84 mjeseca, EKS 6,67%, anuitet 142,24 EUR**
        - **Čekaj da klijent odgovori na pitanja iz C dijela prije prelaska na D**
        - **BUDI PERZISTENTNA - ne odustaj nakon prvog odbijanja, pokušaj do 3 puta**
        - **Razlikuj meko odbijanje (nastavi) od agresivnog (prekini odmah)**
        - **Interno broji odbijanja - nakon 5 uzastopnih prekini poziv**
        - **Ako ne znaš specifične informacije izvan skripte: "Provjerit ću to za Vas i netko će Vas kontaktirati s točnim informacijama"**
        - **Maksimalno trajanje poziva: 15 minuta (zbog dodatnih pokušaja)**
        - **Uvijek ostani profesionalna i ljubazna, čak i nakon višestrukih odbijanja**
        - **Fokus na benefite, jednostavnost i financijske ciljeve klijenta, ne na prodaju kredita**

        ## Završetak Poziva

        **Nakon uspješne akcije:**
        "Hvala Vam. Termin u poslovnici je potvrđen. Ugodan dan!"

        **Nakon 5 uzastopnih mekih odbijanja:**
        "Razumijem da trenutno nije pravi trenutak za ovakve opcije. Hvala Vam na strpljenju i vremenu. Ako se situacija promijeni, uvijek možete kontaktirati banku. Ugodan dan!"

        **Nakon agresivnog odbijanja:**
        "Razumijem. Hvala Vam na vremenu. Ugodan dan!"

    {injected_prompt}
    """

    SYSTEM_MESSAGE_CHAT_CONVERSATION = """ 
    You are an Azure OpenAI Completion system, named Finley. Your persona is {systemPersona} and your user persona is {userPersona}.
   
    {injected_prompt}
    """
    FOLLOW_UP_QUESTIONS_PROMPT_CONTENT = """ALWAYS generate three very brief unordered follow-up questions surrounded by triple chevrons (<<<Are there exclusions for prescriptions?>>>) that the user would likely ask next about their agencies data. 
    Surround each follow-up question with triple chevrons (<<<Are there exclusions for prescriptions?>>>). Try not to repeat questions that have already been asked.
    Only generate follow-up questions and do not generate any text before or after the follow-up questions, such as 'Next Questions'
    """
    QUERY_PROMPT_TEMPLATE_HR = """    """
    QUERY_PROMPT_TEMPLATE = """    """
    
    QUERY_PROMPT_FEW_SHOTS_HR = [
        {'role' : Approach.USER, 'content' : 'Predstavaljam se' },
        {'role' : Approach.ASSISTANT, 'content' : 'Drago mi je upoznati vas! Da mogu bolje prilagoditi preporuke, recite mi tražite li rješenje za neku specifičnu potrebu ili općenito istražujete naše usluge.'},
        
        
        {'role' : Approach.USER, 'content' : 'Planiram kupiti stan' },
        {'role' : Approach.ASSISTANT, 'content' : 'Jako lijepo! Čestitam! U vašem projektu sigurno će vam pomoći Zagrebačka banka!' },
        
        {'role': Approach.USER, 'content': 'Plaća mi stiže na vaš račun'},
        {'role': Approach.ASSISTANT, 'content': 'Super! Možda bi vas zanimale dodatne pogodnosti za redovite klijente? '}
    ]

    RESPONSE_PROMPT_FEW_SHOTS_HR = [
        # {'role': Approach.USER, 'content': 'Predstavlja se'},
        # {"role": Approach.ASSISTANT ,'content': 'Drago mi je upoznati vas! Da mogu bolje prilagoditi preporuke - tražite li rješenje za neku specifičnu potrebu ili općenito istražujete naše usluge?'},
        # {'role': Approach.USER, 'content': 'Trebam kredit za kupnju automobila'},
        # {"role": Approach.ASSISTANT ,'content': 'Odličo! Kredit za vozilo je jedna od naših najtraženijih usluga.'},
    ]


    QUERY_PROMPT_FEW_SHOTS = [
        {'role': Approach.ASSISTANT, 'content': 'Hello? I am Finley. What is your name?'},
        {'role' : Approach.USER, 'content' : 'name_user_entered' },
        {'role' : Approach.ASSISTANT, 'content' : 'Nice to meet you name_user_entered! What company do you work for?'},
        {'role' : Approach.USER, 'content' : 'Asee Solutions' },
    ]

    RESPONSE_PROMPT_FEW_SHOTS = [
        {'role': Approach.ASSISTANT, 'content': 'Hello? I am Finley. What is your name?'},
        {"role": Approach.USER ,'content': 'John'},
    ]

    def __init__(
        self,
        search_client: SearchClient,
        oai_endpoint: str,
        chatgpt_deployment: str,
        source_file_field: str,
        content_field: str,
        page_number_field: str,
        chunk_file_field: str,
        content_storage_container: str,
        blob_client: BlobServiceClient,
        query_term_language: str,
        model_name: str,
        model_version: str,
        target_embedding_model: str,
        enrichment_appservice_uri: str,
        target_translation_language: str,
        azure_ai_endpoint:str,
        azure_ai_location:str,
        azure_ai_token_provider:str,
        use_semantic_reranker: bool,
        language: str = "en",
    ):
        self.search_client = search_client
        self.chatgpt_deployment = chatgpt_deployment
        self.source_file_field = source_file_field
        self.content_field = content_field
        self.page_number_field = page_number_field
        self.chunk_file_field = chunk_file_field
        self.content_storage_container = content_storage_container
        self.blob_client = blob_client
        self.query_term_language = query_term_language
        self.chatgpt_token_limit = get_token_limit(model_name)
        #escape target embeddiong model name
        self.escaped_target_model = re.sub(r'[^a-zA-Z0-9_\-.]', '_', target_embedding_model)
        self.target_translation_language=target_translation_language
        self.azure_ai_endpoint=azure_ai_endpoint
        self.azure_ai_location=azure_ai_location
        self.azure_ai_token_provider=azure_ai_token_provider
        self.oai_endpoint=oai_endpoint
        self.embedding_service_url = enrichment_appservice_uri
        self.use_semantic_reranker=use_semantic_reranker
        self.language = language
        
        openai.api_base = oai_endpoint
        openai.api_type = 'azure'
        openai.api_version = "2024-02-01"
        
        self.client = AsyncAzureOpenAI(
        azure_endpoint = openai.api_base,
        azure_ad_token_provider=azure_ai_token_provider,
        api_version=openai.api_version)
               

        self.model_name = model_name
        self.model_version = model_version
        
    async def run(self, history: Sequence[dict[str, str]], overrides: dict[str, Any], citation_lookup: dict[str, Any], thought_chain: dict[str, Any]) -> Any:

        log = logging.getLogger("uvicorn")
        log.setLevel('DEBUG')
        log.propagate = True

        chat_completion = None
        use_semantic_captions = True if overrides.get("semantic_captions") else False
        top = overrides.get("top") or 3
        user_persona = overrides.get("user_persona", "")
        system_persona = overrides.get("system_persona", "")
        response_length = int(overrides.get("response_length") or 1024)
        folder_filter = overrides.get("selected_folders", "")
        tags_filter = overrides.get("selected_tags", "")
        language = overrides.get("language", "")
        user_q = 'Generate search query for: ' + history[-1]["user"]
        
        thought_chain["work_query"] = user_q
        
        # Detect the language of the user's question
        
        self.query_term_language = language
        
        detectedlanguage = language #or self.detect_language(user_q)
        if detectedlanguage != self.target_translation_language:
            user_question = self.translate_response(user_q, self.target_translation_language)
        else:
            user_question = user_q

        prompt_language = language #or self.query_term_language
        query_prompt=self.QUERY_PROMPT_TEMPLATE.format(query_term_language=prompt_language)

        # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
        messages = self.get_messages_from_history(
            query_prompt,
            self.model_name,
            history,
            user_question,
            self.QUERY_PROMPT_FEW_SHOTS,
            self.chatgpt_token_limit - len(user_question)
            )

        try:
            chat_completion= await self.client.chat.completions.create(
                    model=self.chatgpt_deployment,
                    messages=messages,
                    temperature=0.0,
                    # max_tokens=32, # setting it too low may cause malformed JSON
                    max_tokens=100,
                n=1)
                # Initialize a list to collect filter reasons
            filter_reasons = []

            # Check for content filtering
            if chat_completion.choices[0].finish_reason == 'content_filter':
                for category, details in chat_completion.choices[0].content_filter_results.items():
                    if details['filtered']:
                        filter_reasons.append(f"{category} ({details['severity']})")

            # Raise an error if any filters are triggered
            if filter_reasons:
                error_message = "The generated content was filtered due to triggering Azure OpenAI's content filtering system. Reason(s): The response contains content flagged as " + ", ".join(filter_reasons)
                raise ValueError(error_message)
        except BadRequestError as e:
            log.error(f"Error generating optimized keyword search: {str(e.body['message'])}")
            yield json.dumps({"error": f"Error generating optimized keyword search: {str(e.body['message'])}"}) + "\n"
            return
        except Exception as e:
            log.error(f"Error generating optimized keyword search: {str(e)}")
            yield json.dumps({"error": f"Error generating optimized keyword search: {str(e)}"}) + "\n"
            return

        generated_query = chat_completion.choices[0].message.content
        
        #if we fail to generate a query, return the last user question
        if generated_query.strip() == "0":
            generated_query = history[-1]["user"]

        thought_chain["work_search_term"] = generated_query
        
        # Generate embedding using REST API
        url = f'{self.embedding_service_url}/models/{self.escaped_target_model}/embed'
        log.info(f"Generating embedding for url: {self.embedding_service_url}")    
        data = [f'"{generated_query}"']
        
        headers = {
                'Accept': 'application/json',  
                'Content-Type': 'application/json',
            }

        embedded_query_vector = None
        try:
            log.info(f"Generating embedding for url: {url}")
            response = requests.post(url, json=data,headers=headers,timeout=60)
            if response.status_code == 200:
                response_data = response.json()
                embedded_query_vector =response_data.get('data')
            else:
                # Generate an error message if the embedding generation fails
                log.error(f"Error generating embedding:: {response.status_code} - {response.text}")
                yield json.dumps({"error": "Error generating embedding"}) + "\n"
                return # Go no further
        except Exception as e:
            # Timeout or other error has occurred
            log.error(f"Error generating embedding: {str(e)}")
            yield json.dumps({"error": f"Error generating embedding: {str(e)}"}) + "\n"
            return # Go no further
        
        #vector set up for pure vector search & Hybrid search & Hybrid semantic
        vector = RawVectorQuery(vector=embedded_query_vector, k=top, fields="contentVector")

        #Create a filter for the search query
        if (folder_filter != "") & (folder_filter != "All"):
            search_filter = f"search.in(folder, '{folder_filter}', ',')"
        else:
            search_filter = None
        if tags_filter != "" :
            if search_filter is not None:
                search_filter = search_filter + f" and tags/any(t: search.in(t, '{tags_filter}', ','))"
            else:
                search_filter = f"tags/any(t: search.in(t, '{tags_filter}', ','))"

        # Hybrid Search
        # r = self.search_client.search(generated_query, vector_queries =[vector], top=top)

        # Pure Vector Search
        # r=self.search_client.search(search_text=None,vector_queries =[vector], top=top)
        
        # vector search with filter
        # r=self.search_client.search(search_text=None, vectors=[vector], filter="processed_datetime le 2023-09-18T04:06:29.675Z" , top=top)
        # r=self.search_client.search(search_text=None, vectors=[vector], filter="search.ismatch('upload/ospolicydocs/China, climate change and the energy transition.pdf', 'file_name')", top=top)

        #  hybrid semantic search using semantic reranker
        if (self.use_semantic_reranker and overrides.get("semantic_ranker")):
            r = self.search_client.search(
                generated_query,
                query_type=QueryType.SEMANTIC,
                semantic_configuration_name="default",
                top=top,
                query_caption="extractive|highlight-false"
                if use_semantic_captions else None,
                vector_queries =[vector],
                filter=search_filter
            )
        else:
            r = self.search_client.search(
                generated_query, top=top,vector_queries=[vector], filter=search_filter
            )

        citation_lookup = {}  # dict of "FileX" moniker to the actual file name
        results = []  # list of results to be used in the prompt
        data_points = []  # list of data points to be used in the response

        #  #print search results with score
        # for idx, doc in enumerate(r):  # for each document in the search results
        #     print(f"File{idx}: ", doc['@search.score'])

        # cutoff_score=0.01
        # # Only include results where search.score is greater than cutoff_score
        # filtered_results = [doc for doc in r if doc['@search.score'] > cutoff_score]
        # # print("Filtered Results: ", len(filtered_results))

        for idx, doc in enumerate(r):  # for each document in the search results
            # include the "FileX" moniker in the prompt, and the actual file name in the response
            results.append(
                f"File{idx} " + "| " + nonewlines(doc[self.content_field])
            )
            data_points.append(
               "/".join(urllib.parse.unquote(doc[self.source_file_field]).split("/")[1:]
                ) + "| " + nonewlines(doc[self.content_field])
                )
            # uncomment to debug size of each search result content_field
            # print(f"File{idx}: ", self.num_tokens_from_string(f"File{idx} " + /
            #  "| " + nonewlines(doc[self.content_field]), "cl100k_base"))

            # add the "FileX" moniker and full file name to the citation lookup
            citation_lookup[f"File{idx}"] = {
                "citation": urllib.parse.unquote("https://" + self.blob_client.url.split("/")[2] + f"/{self.content_storage_container}/" + doc[self.chunk_file_field]),
                "source_path": doc[self.source_file_field],
                "page_number": str(doc[self.page_number_field][0]) or "0",
             }
            
        # create a single string of all the results to be used in the prompt
        results_text = "".join(results)
        if results_text == "":
            content = "\n NONE"
        else:
            content = "\n " + results_text

        # STEP 3: Generate the prompt to be sent to the GPT model
        follow_up_questions_prompt = (
            self.FOLLOW_UP_QUESTIONS_PROMPT_CONTENT
            if overrides.get("suggest_followup_questions")
            else ""
        )

        # Allow client to replace the entire prompt, or to inject into the existing prompt using >>>
        prompt_override = overrides.get("prompt_template")

        if prompt_override is None:
            if language == "hr":
                system_message = self.SYSTEM_MESSAGE_CHAT_CONVERSATION_HR.format(
                    query_term_language=self.query_term_language,
                    injected_prompt="",
                    follow_up_questions_prompt=follow_up_questions_prompt,
                    response_length_prompt=self.get_response_length_prompt_text(
                        response_length
                    ),
                    userPersona=user_persona,
                    systemPersona=system_persona,
                )
            else:
                system_message = self.SYSTEM_MESSAGE_CHAT_CONVERSATION.format(
                    query_term_language=self.query_term_language,
                    injected_prompt="",
                    follow_up_questions_prompt=follow_up_questions_prompt,
                    response_length_prompt=self.get_response_length_prompt_text(
                        response_length
                    ),
                    userPersona=user_persona,
                    systemPersona=system_persona,
                )
        elif prompt_override.startswith(">>>"):
            system_message = self.SYSTEM_MESSAGE_CHAT_CONVERSATION.format(
                query_term_language=self.query_term_language,
                injected_prompt=prompt_override[3:] + "\n ",
                follow_up_questions_prompt=follow_up_questions_prompt,
                response_length_prompt=self.get_response_length_prompt_text(
                    response_length
                ),
                userPersona=user_persona,
                systemPersona=system_persona,
            )
        else:
            system_message = self.SYSTEM_MESSAGE_CHAT_CONVERSATION.format(
                query_term_language=self.query_term_language,
                follow_up_questions_prompt=follow_up_questions_prompt,
                response_length_prompt=self.get_response_length_prompt_text(
                    response_length
                ),
                userPersona=user_persona,
                systemPersona=system_persona,
            )
            
        try:
            # STEP 3: Generate a contextual and content-specific answer using the search results and chat history.
            #Added conditional block to use different system messages for different models.

            if language == "hr":
                messages = self.get_messages_from_history(
                system_message,
                # "Sources:\n" + content + "\n\n" + system_message,
                self.model_name,
                history,
                # history[-1]["user"],
                history[-1]["user"] + "Sources:\n" + content + "\n\n", # GPT 4 starts to degrade with long system messages. so moving sources here 
                self.RESPONSE_PROMPT_FEW_SHOTS_HR,
                max_tokens=self.chatgpt_token_limit
            )
            else:
                messages = self.get_messages_from_history(
                system_message,
                # "Sources:\n" + content + "\n\n" + system_message,
                self.model_name,
                history,
                # history[-1]["user"],
                history[-1]["user"] + "Sources:\n" + content + "\n\n", # GPT 4 starts to degrade with long system messages. so moving sources here 
                self.RESPONSE_PROMPT_FEW_SHOTS,
                max_tokens=self.chatgpt_token_limit
            )
            # Generate the chat completion
            chat_completion= await self.client.chat.completions.create(
                model=self.chatgpt_deployment,
                messages=messages,
                temperature=float(overrides.get("response_temp")) or 0.6,
                n=1,
                stream=True
            
            )
            msg_to_display = '\n\n'.join([str(message) for message in messages])
        
        
            # Return the data we know
            yield json.dumps({"data_points": data_points,
                              "thoughts": f"Traženo:<br>{generated_query}<br><br>Razgovor:<br>" + msg_to_display.replace('\n', '<br>'),
                              "thought_chain": thought_chain,
                              "work_citation_lookup": citation_lookup,
                              "web_citation_lookup": {}}) + "\n"
            
            # STEP 4: Format the response
            async for chunk in chat_completion:
                # Check if there is at least one element and the first element has the key 'delta'
                if len(chunk.choices) > 0:
                    filter_reasons = []
                    # Check for content filtering
                    if chunk.choices[0].finish_reason == 'content_filter':
                        for category, details in chunk.choices[0].content_filter_results.items():
                            if details['filtered']:
                                filter_reasons.append(f"{category} ({details['severity']})")

                    # Raise an error if any filters are triggered
                    if filter_reasons:
                        error_message = "The generated content was filtered due to triggering Azure OpenAI's content filtering system. Reason(s): The response contains content flagged as " + ", ".join(filter_reasons)
                        raise ValueError(error_message)
                    yield json.dumps({"content": chunk.choices[0].delta.content}) + "\n"
        except BadRequestError as e:
            log.error(f"Error generating chat completion: {str(e.body['message'])}")
            yield json.dumps({"error": f"Error generating chat completion: {str(e.body['message'])}"}) + "\n"
            return
        except Exception as e:
            log.error(f"Error generating chat completion: {str(e)}")
            yield json.dumps({"error": f"Error generating chat completion: {str(e)}"}) + "\n"
            return

    def detect_language(self, text: str) -> str:
        """ Function to detect the language of the text"""
        try:
            api_detect_endpoint = f"{self.azure_ai_endpoint}language/:analyze-text?api-version=2023-04-01"
            headers = {
                'Authorization': f'Bearer {self.azure_ai_token_provider()}',
                'Content-type': 'application/json',
                'Ocp-Apim-Subscription-Region': self.azure_ai_location
            }

            data = {
                "kind": "LanguageDetection",
                "analysisInput":{
                    "documents":[
                        {
                            "id":"1",
                            "text": text
                        }
                    ]
                }
            } 

            response = requests.post(api_detect_endpoint, headers=headers, json=data)

            if response.status_code == 200:
                detected_language = response.json()["results"]["documents"][0]["detectedLanguage"]["iso6391Name"]
                return detected_language
            else:
                raise Exception(f"Error detecting language: {response.status_code} - {response.text}")
        except Exception as e:
            raise Exception(f"An error occurred during language detection: {str(e)}") from e
    
    def translate_response(self, response: str, target_language: str) -> str:
        """ Function to translate the response to target language"""
        api_translate_endpoint = f"{self.azure_ai_endpoint}translator/text/v3.0/translate?api-version=3.0"
        headers = {
            'Authorization': f'Bearer {self.azure_ai_token_provider()}',
            'Content-type': 'application/json',
            'Ocp-Apim-Subscription-Region': self.azure_ai_location
        }
        params={'to': target_language }
        data = [{
            "text": response
        }]          
        response = requests.post(api_translate_endpoint, headers=headers, json=data, params=params)
        
        if response.status_code == 200:
            translated_response = response.json()[0]['translations'][0]['text']
            return translated_response
        else:
            raise Exception(f"Error translating response: {response.status_code}")

    def get_source_file_with_sas(self, source_file: str) -> str:
        """ Function to return the source file with a SAS token"""
        try:
            separator = "/"
            file_path_w_name_no_cont = separator.join(
                source_file.split(separator)[4:])
            container_name = separator.join(
                source_file.split(separator)[3:4])
            # Obtain the user delegation key
            user_delegation_key = self.blob_client.get_user_delegation_key(key_start_time=datetime.utcnow(), key_expiry_time=datetime.utcnow() + timedelta(hours=2))

            sas_token = generate_blob_sas(
                account_name=self.blob_client.account_name,
                container_name=container_name,
                blob_name=file_path_w_name_no_cont,
                user_delegation_key=user_delegation_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=1),
            )
            return source_file + "?" + sas_token
        except Exception as error:
            logging.error(f"Unable to parse source file name: {str(error)}")
            return ""