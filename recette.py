from uuid import uuid4

class Recette:
    def __init__(self,nom_recette,ingredients,temps_preparation,gestionnaire):
        self.nom_recette=nom_recette
        self.ingredients=ingredients
        self.temps_preparation=temps_preparation
        self.inc=uuid4()
        self.gestionnaire=gestionnaire

    def ajouter_recette(self):
        self.gestionnaire[self.inc] = self

    #Les fonctions de recherche en fonction du nom, des ingrédients et de la durée
    def recherche_par_nom(self,element):
        for recette in self.gestionnaire.values():
            if recette.nom_recette.capitalize() == element.capitalize():
                print(recette.nom_recette, recette.ingredients, recette.temps_preparation)
                break
        else:
            print("Aucune recette disponible au nom de ", element)

    def recherche_par_ingredient(self,element):
        flag=0
        for recette in self.gestionnaire.values():
            for i in recette.ingredients:
                if i.capitalize() ==element.capitalize():
                    print(recette.nom_recette, recette.ingredients, recette.temps_preparation)
                    flag=1
        if flag==0:
            print("Aucune recette disponible a partir de l'ingrédient ", element)

    def recherche_par_duree(self,element):
        flag=0
        for recette in self.gestionnaire.values():
            if recette.temps_preparation ==int(element):
                print(recette.nom_recette, recette.ingredients, recette.temps_preparation)
                flag=1
        if flag==0:
            print("Aucune recette disponible a partir du temps de préparation ", element)


    def rechercher_recette(self,element):
        choix=input("Voulez vous rechercher par :\n1-Nom de la recette\n2-Ingredient\n3-Temps de préparation\nChoisir uniquement le chiffre : ")
        while True:
            if choix in ['1','2','3']:
                choix = int(choix)
                break
            else:
                choix = input("Voulez vous rechercher par :\n1-Nom de la recette\n2-Ingredient\n3-Temps de préparation\nChoisir uniquement le chiffre : ")

        match choix:
            case 1:
                print("Recherche par recette")
                self.recherche_par_nom(element)

            case 2:
                print("Recherche par ingrédient")
                self.recherche_par_ingredient(element)

            case 3:
                print("Recherche par Temps de préparation")
                self.recherche_par_duree( element)

            case _:
                print("Au cas probable")

if __name__ == '__main__':
    carnet=Recette("Poulet",["Poulet","Sel","Poivre","Herbe arômatique"],60, {})
    carnet.ajouter_recette()

    carnet.rechercher_recette("poulet")

