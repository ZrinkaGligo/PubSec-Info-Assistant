import styles from './LegalAssistantEntry.module.css';
import legalAssistantIcon from '../../assets/icon-legal-ai.webp';
import { useTranslation } from "react-i18next";

interface LegalAssistantEntryProps{
    onLegalAssistantEntryClicked: (upit: string) => void;
}
export const LegalAssistantEntry = ({onLegalAssistantEntryClicked} : LegalAssistantEntryProps) => {
    const { t } = useTranslation();

    return (
            <>
                <div className={styles.wrap}> 
                    <h1> {t("LegalAssistantEntry.LegalAssistant")}</h1>
                    <img src={legalAssistantIcon} alt="Description of image" className={styles.image} onClick={()=>onLegalAssistantEntryClicked('TEST')} />
                </div>
             </>
    )};


export default LegalAssistantEntry;

