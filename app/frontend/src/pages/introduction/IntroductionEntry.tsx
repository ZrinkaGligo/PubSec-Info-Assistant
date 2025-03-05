import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import IntrodctionImage from '../../assets/MeetFinley_v1.jpg';
import styles from './IntroductionEntry.module.css';


const IntroductionEntry = () => {
    const navigate = useNavigate();
    const handleImageClick = (language: string) => {
        navigate("/IntroductionChat", { state: { isFirstRedirect: true, language: {language}} });
    };
    return (
        <div className={styles.introductionMainStyle}>
            <img src = {IntrodctionImage}
            alt = "Hello I am Finely! How can I help you today?"
            className={styles.image}>
            </img>
            <div className={styles.buttonContainer} >
            <button className={styles.button} onClick={() => handleImageClick("EN")}>
                    LET'S GO!
            </button>
           
            <button className={styles.button} onClick={() => handleImageClick("HR")}>
                    KRENIMO!
            </button>
            </div>
        </div>
    );
}

export default IntroductionEntry;    