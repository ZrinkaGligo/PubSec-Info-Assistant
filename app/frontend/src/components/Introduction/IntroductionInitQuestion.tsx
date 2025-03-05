import styles from './IntroductionInitQuestion.module.css';
import finleyIcon from '../../assets/finley.jpg';


const IntroductionInitQuestion = () => {
    return (
        <div className={styles.tableStyle}>
            <div className={styles.rowStyle}>
                <img src={finleyIcon} alt="Description of image" className={styles.image} />
                <div className={styles.textColumn}>Hej! Ja sam Finley! Možete li se predstaviti?</div>
            </div>
            <div className={styles.rowStyle}>
               <div className={styles.columnStyle}> Kako se zovete, u kojoj tvrtki radite i koja je vaša pozicija?</div>
            </div>
        </div>
    );          
}   

export {IntroductionInitQuestion};