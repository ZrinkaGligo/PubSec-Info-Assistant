import styles from './IntroductionInitQuestion.module.css';
import finleyIcon from '../../assets/Finley.jpg';
import { useTranslation } from "react-i18next";

const IntroductionInitQuestion = () => {
    const { t } = useTranslation();
    return (
        <div className={styles.tableStyle}>
            <div className={styles.rowStyle}>
                <img src={finleyIcon} alt="Description of image" className={styles.image} />
                <div className={styles.textColumn}>{t('finley-introduction')}</div>
            </div>
            <div className={styles.rowStyle}>
               <div className={styles.columnStyle}>{t('finley-init-question')}</div>
            </div>
        </div>
    );          
}   

export {IntroductionInitQuestion};