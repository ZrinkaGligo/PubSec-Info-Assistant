import React, { useState, useEffect, useCallback } from 'react';
import { Conversation } from '@elevenlabs/client';
import styles from './ElevenLabsMain.module.css';
import { useTranslation } from "react-i18next";
import { useLocation } from 'react-router-dom';
import SlusalicaZelena from "../../assets/Slusalica zelena.svg";
import SlusalicaCrvena from "../../assets/Slusalica crvena.svg";

// TypeScript tipovi
interface ConversationMode {
  mode: 'speaking' | 'listening';
}

type ConnectionStatus = 'Spojen' | 'Odspojen';
type AgentStatus = 'Priča' | 'Sluša';
type salesType = 'Kredit' | 'Paket';

const ElevenLabsMain = () => {
  const location = useLocation();
  // State hook-ovi
  const { t } = useTranslation();
  const [conversation, setConversation] = useState<any>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('Odspojen');
  const [agentStatus, setAgentStatus] = useState<AgentStatus>('Sluša');
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [agentSalesType, setAgentSalesType] = useState<salesType>('Kredit');
  const [agentId, setAgentId] = useState<string>('agent_01jyp4pajffdsr8h5nm4z5h7p5')
  const [name, setName] = useState('');
  const [sales_type, setSalesType] = useState<salesType>('Kredit');
  const [account_bundle, setAccountBundle] = useState('');
  const [additionalPrompt, setAdditionalPrompt] = useState('');

  const getAgentIdBySalesType = (salesType: salesType): string => {
    switch (salesType) {
        case 'Kredit':
            return 'agent_01jyp4pajffdsr8h5nm4z5h7p5'; 
        case 'Paket':
            return 'agent_01jyrft17jfvv8njm4h1etxjq8'; 
        default:
            return 'agent_01jyp4pajffdsr8h5nm4z5h7p5'; 
    }
  };
  const getAdditionalPrompt = (salesType: salesType, name : string, account_bundle : string) => {
  console.log("unutar getAdditionalPrompt su: " + name + " " + account_bundle);
   if (salesType === 'Kredit') {
       return `Ime korisnika je: ${name}`;
   } else if (salesType === 'Paket') {
       return `Ime korisnika je ${name}. Trenutno ima paket: ${account_bundle}`;
   }
   return '';
  }

  useEffect(() => {
        const { salesType, nameParam, accountBundle } = location.state || {};
        if (salesType === 'Kredit' || salesType === 'Paket') {
            
            setAgentSalesType(salesType);
            setAgentId(getAgentIdBySalesType(salesType))

            setName(nameParam);
            setAccountBundle(accountBundle);
        }
    }, [location.state]);



  // Funkcija za pokretanje razgovora
  const startConversation = useCallback(async () => {
    try {
      
      let tempPrompt = getAdditionalPrompt(sales_type, name, account_bundle);
      await navigator.mediaDevices.getUserMedia({ audio: true });
      
      const newConversation = await Conversation.startSession({
       
      agentId: agentId,
      // overrides: {
      //   agent: {
      //     prompt: {
      //       prompt: `${tempPrompt}. Prilagodi razgovor prema ovim informacijama.`
      //     },
      //     firstMessage: `test`,
      //     language: "hr"
      //   }
      // },
      onConnect: () => {
          setConnectionStatus('Spojen');
          console.log(isConnected);
          setIsConnected(true);
        },
        onDisconnect: () => {
          setConnectionStatus('Odspojen');
          console.log(isConnected);
          setIsConnected(false);
        },
        onError: (error: any) => {
          console.error('Error:', error);
        },
        onModeChange: (mode: ConversationMode) => {
          setAgentStatus(mode.mode === 'speaking' ? 'Priča' : 'Sluša');
        },
      });
      
      setConversation(newConversation);
    } catch (error) {
      console.error('Failed to start conversation:', error);
    }
  }, [sales_type, name, account_bundle]);

  // Funkcija za zaustavljanje razgovora
  const stopConversation = useCallback(async () => {
    if (conversation) {
      await conversation.endSession();
      setConversation(null);
    }
  }, [conversation]);

  return (
    <div className={styles.wrapper}>
      <div className={styles.container}>
        <div className={styles.title}>
            {t("ElevenLabsMain.Title")}
        </div>
        
        <div className={styles.buttonContainer}>
              <button className={`${styles.button} ${styles.startButton}`} disabled={isConnected} onClick={startConversation}>
                <span className={styles.content}>
                  <span className={styles.exampleText}> {t("ElevenLabsMain.Start")} </span>
                  <img src = {SlusalicaZelena} alt = "" className={styles.phoneIcon}/>
                 </span>
              </button>
            <button className={`${styles.button} ${styles.stopButton}`} disabled={!isConnected} onClick={stopConversation}>
                <span className={styles.content}>
                  <span className={styles.exampleText}>{t("ElevenLabsMain.Stop")} </span>
                  <img src = {SlusalicaCrvena} alt = "" className={styles.phoneIcon}/>
                </span>
                
            </button>
        </div> 

        
        <div className={styles.statusContainer}>
          <div className={styles.statusItem}>
            <span className={styles.statusLabel}>Status:</span>
            <span className={`${styles.statusValue} ${connectionStatus === 'Spojen' ? styles.connected : styles.disconnected}`}>
              {connectionStatus}
            </span>
          </div>
          <div className={styles.statusItem}>
            <span className={styles.statusLabel}>Agent:</span>
            <span className={`${styles.statusValue} ${agentStatus === 'Priča' ? styles.speaking : styles.listening}`}>
              {agentStatus}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ElevenLabsMain;