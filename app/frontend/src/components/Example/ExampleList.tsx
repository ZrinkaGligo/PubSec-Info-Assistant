// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES_InterniAkti: ExampleModel[] = [
    { text: "Koje su ključne obaveze banke u zaštiti osobnih podataka klijenata prema GDPR-u?", value: "Koje su ključne obaveze banke u zaštiti osobnih podataka klijenata prema GDPR-u" },
    { text: "Koji su postupci zaposlenika defirani u slučaju primjećivanja pranja novca (AML)?", value: "Koji su postupci zaposlenika defirani u slučaju primjećivanja pranja novca (AML)?" },
    { text: "Koji su glavni interni i regulatorni zahtjevi koje banka mora ispuniti prilikom odobravanja donacija?", value: "Koji su glavni interni i regulatorni zahtjevi koje banka mora ispuniti prilikom odobravanja donacija?" }
];
const EXAMPLES_InterniAkti_EN: ExampleModel[] = [
    { text: "What are the key obligations of a bank in protecting client's personal data under GDPR?", value: "What are the key obligations of a bank in protecting clients' personal data under GDPR?" },
    { text: "What procedures are defined for employees in case of detecting money laundering (AML)?", value: "What procedures are defined for employees in case of detecting money laundering (AML)?" },
    { text: "What are the main internal and regulatory requirements that a bank must meet when approving donations?", value: "What are the main internal and regulatory requirements that a bank must meet when approving donations?" }
];
const EXAMPLES: ExampleModel[] = [
    { text: "Kako se odluke Europskog suda primjenjuju u Hrvatskoj?", value: "Kako se odluke Europskog suda primjenjuju u Hrvatskoj?" },
    { text: "Molio bih primjere revizija odluka županijskih sudova", value: "Molio bih primjere revizija odluka županijskih sudova" },
    { text: "Kako se određuje drugi nadležni sud u Hrvatskoj?", value: "Kako se određuje drugi nadležni sud u Hrvatskoj?" }
    
    
];
const EXAMPLES_EN: ExampleModel[] = [
    { text: "How are the decisions of the European Court applied in Croatia?", value: "How are the decisions of the European Court applied in Croatia?" },
    { text: "I would like examples of revisions of court decisions", value: "I would like examples of revisions of court decisions" },
    { text: "How is the second competent court determined in Croatia?", value: "How is the second competent court determined in Croatia?" }
];

const language = () => {
    return localStorage.getItem("lang");
}
const GetExamples = (topic: string) => {
    if(language() === "hr"){
        if (topic === "IA") {
            return EXAMPLES_InterniAkti;
        }
        else if (topic === "LA") {
            return EXAMPLES;
        }
        else {
            return EXAMPLES;
        }
    }
    else{
            if (topic === "IA") {
                return EXAMPLES_InterniAkti_EN;
            }
            else if (topic === "LA") {
                return EXAMPLES_EN;
            }
            else {
                return EXAMPLES_EN;
            }
    }
}
interface Props {
    onExampleClicked: (value: string) => void;
    topic: string;
}


export const ExampleList = ({ onExampleClicked, topic }: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {GetExamples(topic).map((x, i) => (
            <li key={i}>
                <Example text={x.text} value={x.value} onClick={onExampleClicked} />
            </li>
            ))}
        </ul>
    );
};
